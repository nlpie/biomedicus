# Copyright 2019 Regents of the University of Minnesota.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from argparse import ArgumentParser
from pathlib import Path

import math
import numpy as np
import tensorflow as tf
from mtap.io.brat import read_brat_document

from biomedicus.sentences.vocabulary import Vocabulary


def encode(l):
    return [x.encode() for x in l]


def serialize_example(priors, tokens, posts, labels):
    features = {
        'priors': tf.train.Feature(bytes_list=tf.train.BytesList(value=encode(priors))),
        'tokens': tf.train.Feature(bytes_list=tf.train.BytesList(value=encode(tokens))),
        'posts': tf.train.Feature(bytes_list=tf.train.BytesList(value=encode(posts))),
        'labels': tf.train.Feature(int64_list=tf.train.Int64List(value=labels)),
    }
    example_proto = tf.train.Example(features=tf.train.Features(feature=features))
    return example_proto.SerializeToString()


def step_sequence(priors, tokens, posts, labels, sequence_length):
    required_pad = sequence_length - len(priors)
    if required_pad > 0:
        yield priors, tokens, posts, labels
    else:
        for i in range(0, len(priors) - sequence_length):
            limit = i + sequence_length
            yield priors[i:limit], tokens[i:limit], posts[i:limit], labels[i:limit]


_whitespace_pattern = re.compile(r'[\w.\']+|\[\*\*.*\*\*\]')


def examples_generator(docs, sequence_length, training):
    for doc in docs:
        priors = []
        words = []
        posts = []
        labels = []
        with read_brat_document(doc) as event:
            document = event.documents['plaintext']
            text = document.text
            try:
                sentences = document.get_label_index('Sentence')
            except KeyError:
                continue
            tokens = [(0, 0)] + [(m.start(), m.end()) for m in
                                 _whitespace_pattern.finditer(text)] + [(len(text), len(text))]

            i = 1
            for sentence in sentences:
                while i < len(tokens) - 1 and tokens[i][0] < sentence.start_index:
                    i += 1
                    if len(priors) > 0:
                        if training:
                            yield from step_sequence(priors, words, posts, labels, sequence_length)
                        else:
                            yield priors, words, posts, labels
                        priors = []
                        words = []
                        posts = []
                        labels = []
                is_start = True
                while i < len(tokens) - 1 and tokens[i][0] in range(sentence.start_index,
                                                                    sentence.end_index):
                    _, prev_end = tokens[i - 1]
                    start, end = tokens[i]
                    next_start, _ = tokens[i + 1]
                    priors.append(text[prev_end:start])
                    words.append(text[start:end])
                    posts.append(text[end:next_start])
                    labels.append(1 if is_start else 0)
                    is_start = False
                    i += 1
                if i == len(tokens) - 1:
                    break
        if len(priors) > 0:
            if training:
                yield from step_sequence(priors, words, posts, labels, sequence_length)
            else:
                yield priors, words, posts, labels


def train_validation(train_file, validation_file, chars_mapping, words, repeat_count=1,
                     batch_size=1):
    dataset = tf.data.TFRecordDataset(filenames=[str(train_file)])

    features = {
        'priors': tf.io.VarLenFeature(tf.string),
        'tokens': tf.io.VarLenFeature(tf.string),
        'posts': tf.io.VarLenFeature(tf.string),
        'labels': tf.io.VarLenFeature(tf.int64)
    }

    def _count_parse_fn(serialized):
        parsed_example = tf.io.parse_single_example(serialized, features)
        labels = parsed_example['labels']
        return labels

    count_parsed = dataset.map(_count_parse_fn)

    def count_fn(current_counts, example):
        labels = example.values
        y, _, count = tf.unique_with_counts(labels)
        update = tf.scatter_nd(tf.expand_dims(y, -1), count, [2])
        return current_counts + update

    counts = count_parsed.reduce([0, 0], count_fn)
    weights, _ = tf.linalg.normalize(tf.cast(counts, tf.float64), 1)

    def _parse_function(serialized):
        parsed_example = tf.io.parse_single_example(serialized, features)
        return (parsed_example['priors'], parsed_example['tokens'], parsed_example['posts'],
                (parsed_example['labels']))

    input_fn = InputFn(chars_mapping, words)

    dataset = (dataset.map(_parse_function)
               .shuffle(buffer_size=256)
               .repeat(repeat_count)
               .batch(batch_size)
               .map(input_fn))

    validation_dataset = (tf.data.TFRecordDataset(filenames=[str(validation_file)])
                          .map(_parse_function)
                          .batch(1)
                          .map(input_fn))

    return dataset, validation_dataset, weights


def convert_to_dataset(input_directory, validation_split, sequence_length):
    docs = list(map(str, Path(input_directory).glob('*/*.txt')))
    np.random.shuffle(docs)
    split = math.ceil(len(docs) * validation_split)
    train_docs = docs[split:]
    validation_docs = docs[:split]

    with tf.io.TFRecordWriter('train.tfrecord') as writer:
        for example in examples_generator(train_docs, sequence_length, True):
            serialized_example = serialize_example(*example)
            writer.write(serialized_example)

    with tf.io.TFRecordWriter('validation.tfrecord') as writer:
        for example in examples_generator(validation_docs, sequence_length, False):
            serialized_example = serialize_example(*example)
            writer.write(serialized_example)


class InputFn:
    def __init__(self, chars_mapping, words):
        keys, values = zip(*chars_mapping.items())
        self.chars_table = tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(keys, values),
            Vocabulary.UNK_CHAR
        )
        self.words_table = tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(words, range(len(words))),
            len(words)
        )

    def __call__(self, priors, words, posts, labels):
        priors = tf.RaggedTensor.from_sparse(priors)
        words = tf.RaggedTensor.from_sparse(words)
        posts = tf.RaggedTensor.from_sparse(posts)

        lowered = tf.strings.lower(words.flat_values)
        normed = words.with_flat_values(lowered)
        normed = tf.strings.regex_replace(normed, "[\\pP\\pS]", "")
        normed = tf.strings.regex_replace(normed, "\\pN", "#")
        flat_lookup = self.words_table.lookup(normed.flat_values)
        normed = normed.with_flat_values(flat_lookup)
        word_ids = normed.to_tensor()

        flat_priors = priors.flat_values
        flat_tokens = words.flat_values
        flat_posts = posts.flat_values

        concatted = tf.concat([
            marker_char(Vocabulary.PREV_TOKEN, flat_priors),
            self._lookup_char_ids(flat_priors),
            marker_char(Vocabulary.TOKEN_BEGIN, flat_priors),
            self._lookup_char_ids(flat_tokens),
            marker_char(Vocabulary.TOKEN_END, flat_priors),
            self._lookup_char_ids(flat_posts),
            marker_char(Vocabulary.NEXT_TOKEN, flat_priors)
        ], axis=-1)
        nested = tf.RaggedTensor.from_row_lengths(concatted,
                                                  tf.cast(priors.row_lengths(), tf.int64))
        character_ids = nested.to_tensor()

        return {
                   'word_ids': word_ids,
                   'character_ids': character_ids
               }, tf.sparse.to_dense(labels) if labels is not None else None

    def _lookup_char_ids(self, chars):
        split = tf.strings.unicode_split(chars, 'UTF-8')
        return tf.RaggedTensor.from_row_lengths(self.chars_table.lookup(split.flat_values),
                                                split.row_lengths())


def marker_char(int_value, like):
    return tf.expand_dims(tf.ones_like(like, dtype=tf.int32) * int_value, -1)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--sequence-length', type=int, default=32)
    parser.add_argument('--validation-split', type=float, default=.2)
    parser.add_argument('input_directory')
    config = parser.parse_args(args)
    convert_to_dataset(config.input_directory, config.validation_split, config.sequence_length)


if __name__ == '__main__':
    main()
