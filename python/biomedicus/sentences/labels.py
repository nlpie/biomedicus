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
import math
import re
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import tensorflow as tf
from mtap.io.brat import read_brat_document


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
            tokens = [(0, 0)] + [(m.start(), m.end()) for m in _whitespace_pattern.finditer(text)] + [(len(text), len(text))]

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
                while i < len(tokens) - 1 and tokens[i][0] in range(sentence.start_index, sentence.end_index):
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


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--sequence-length', type=int, default=32)
    parser.add_argument('--validation-split', type=float, default=.2)
    parser.add_argument('input_directory')
    config = parser.parse_args(args)
    convert_to_dataset(config.input_directory, config.validation_split, config.sequence_length)


if __name__ == '__main__':
    main()
