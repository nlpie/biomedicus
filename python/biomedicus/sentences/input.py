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
from pathlib import Path

import math
import numpy as np
import torch
from torch.nn.utils.rnn import pad_sequence

from biomedicus.sentences.vocabulary import Vocabulary, get_char

_whitespace_pattern = re.compile(r'((?!_)[\w.\'])+|\[\*\*.*?\*\*\]')
_digit = re.compile(r'[0-9]')
_punct = re.compile(r'[.\']')
_identifier = re.compile(r'\[\*\*.*\*\*\]')


class Dataset:
    def __init__(self, batch_size):
        self.char_ids = []
        self.word_ids = []
        self.labels = []
        self.lengths = []
        self.batch_size = batch_size

    @property
    def n_batches(self):
        return len(self.lengths) // self.batch_size

    def append(self, char_ids, word_ids, labels):
        self.char_ids.append(char_ids)
        self.word_ids.append(word_ids)
        self.labels.append(labels)
        self.lengths.append(len(labels))

    def build(self):
        self.char_ids = [torch.tensor(x) for x in self.char_ids]
        self.word_ids = [torch.tensor(x) for x in self.word_ids]
        self.labels = [torch.tensor(x) for x in self.labels]
        self.lengths = torch.tensor(self.lengths)

    def batches(self, shuffle=True):
        indices = np.arange(len(self.lengths))
        if shuffle:
            np.random.shuffle(indices)
        for batch in range(self.n_batches):
            batch_indices = indices[batch * self.batch_size:(batch + 1) * self.batch_size]
            char_ids = pad_sequence([self.char_ids[idx] for idx in batch_indices], batch_first=True)
            word_ids = pad_sequence([self.word_ids[idx] for idx in batch_indices], batch_first=True)
            labels = pad_sequence([self.labels[idx] for idx in batch_indices], batch_first=True)
            lengths = self.lengths[batch_indices]
            yield (char_ids, word_ids), labels, lengths


class InputMapping:
    def __init__(self, char_mapping, words, word_length, device=None):
        self.char_mapping = char_mapping
        self.word_mapping = {word: i for i, word in enumerate(words)}
        self.word_length = word_length
        self.device = device or 'cpu'

    def load_dataset(self, input_directory, validation_split, batch_size, sequence_length):
        class_counts = [0, 0]
        docs = list(map(str, Path(input_directory).glob('*/*.txt')))
        np.random.shuffle(docs)
        split = math.ceil(len(docs) * validation_split)
        train_docs = docs[split:]
        validation_docs = docs[:split]

        train = Dataset(batch_size)
        for char_ids, word_ids, labels in self.examples_generator(train_docs, sequence_length, True,
                                                                  class_counts):
            train.append(char_ids, word_ids, labels)

        validation = Dataset(1)
        for char_ids, word_ids, labels in self.examples_generator(validation_docs, sequence_length,
                                                                  False, class_counts):
            validation.append(char_ids, word_ids, labels)

        # there are many more negative examples (label == 0) than positive examples, so we weight
        # positive values according to the ratios, so that precision and recall end up being equally
        # important during training
        pos_weight = class_counts[0] / class_counts[1]

        train.build()
        validation.build()
        return train, validation, pos_weight

    def transform_text(self, text):
        char_ids = []
        word_ids = []
        actual_tokens = [(m.start(), m.end()) for m in _whitespace_pattern.finditer(text)]
        tokens = [(0, 0)] + actual_tokens + [(len(text), len(text))]
        start_of_sequence = True
        for i in range(1, len(tokens) - 1):
            local_char_ids, local_word_id = self.transform_word(i, start_of_sequence,
                                                                text, tokens)
            char_ids.append(local_char_ids)
            word_ids.append(local_word_id)
            start_of_sequence = False
        return (
            actual_tokens,
            torch.tensor([char_ids], device=self.device),
            torch.tensor([word_ids], device=self.device)
        )

    def examples_generator(self, docs, sequence_length, training, class_counts):
        from mtap.serialization.brat import read_brat_document
        for doc in docs:
            char_ids = []
            word_ids = []
            labels = []
            start_of_sequence = True
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
                        if len(labels) > 0:
                            if training:
                                yield from step_sequence(char_ids, word_ids, labels,
                                                         sequence_length)
                            else:
                                yield char_ids, word_ids, labels
                            char_ids = []
                            word_ids = []
                            labels = []
                            start_of_sequence = True
                    start_of_sentence = True
                    while i < len(tokens) - 1 and tokens[i][0] in range(sentence.start_index,
                                                                        sentence.end_index):
                        local_char_ids, local_word_id = self.transform_word(i, start_of_sequence,
                                                                            text, tokens)
                        char_ids.append(local_char_ids)
                        word_ids.append(local_word_id)
                        label = 1 if start_of_sentence else 0
                        class_counts[label] += 1
                        labels.append(label)
                        start_of_sentence = False
                        start_of_sequence = False
                        i += 1
                    if i == len(tokens) - 1:
                        break
            if len(labels) > 0:
                if training:
                    yield from step_sequence(char_ids, word_ids, labels, sequence_length)
                else:
                    yield char_ids, word_ids, labels

    def transform_word(self, i, start_of_sequence, text, tokens):
        _, prev_end = tokens[i - 1]
        start, end = tokens[i]
        next_start, _ = tokens[i + 1]
        prior = text[prev_end:start]
        word = text[start:end]
        post = text[end:next_start]
        local_char_ids = self.lookup_char_ids(prior, word, post, start_of_sequence)
        local_word_id = self.lookup_word_id(word)
        return local_char_ids, local_word_id

    def lookup_char_ids(self, prior, word, post, start_of_sequence):
        char_ids = ([Vocabulary.BEGIN_SEQUENCE if start_of_sequence else Vocabulary.PREV_TOKEN]
                    + [get_char(self.char_mapping, c) for c in prior]
                    + [Vocabulary.TOKEN_BEGIN]
                    + [get_char(self.char_mapping, c) for c in word]
                    + [Vocabulary.TOKEN_END]
                    + [get_char(self.char_mapping, c) for c in post]
                    + [Vocabulary.NEXT_TOKEN])
        if len(char_ids) > self.word_length:
            return char_ids[:self.word_length]
        elif len(char_ids) < self.word_length:
            padded = [Vocabulary.PADDING for _ in range(self.word_length)]
            padded[:len(char_ids)] = char_ids
            return padded
        else:
            return char_ids

    def lookup_word_id(self, word):
        if _identifier.match(word):
            word = 'IDENTIFIER'
        else:
            word = word.lower()
            word = _punct.sub('', word)
            word = _digit.sub('#', word)
        local_word_id = self.word_mapping.get(word, len(self.word_mapping))
        return local_word_id


def step_sequence(char_ids, word_ids, labels, sequence_length):
    length = len(labels)
    required_pad = sequence_length - length
    if required_pad > 0:
        yield char_ids, word_ids, labels
    else:
        for i in range(0, length - sequence_length):
            limit = i + sequence_length
            yield char_ids[i:limit], word_ids[i:limit], labels[i:limit]
