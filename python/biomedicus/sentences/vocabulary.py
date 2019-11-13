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
import os
from abc import abstractmethod, ABC

import numpy as np
import pathlib
import re
from typing import Optional, AnyStr, Iterable, Tuple, List

from biomedicus.tokenization import Token, detect_space_after


class Vocabulary(object):
    """The character, label, and word embeddings vocabulary.

    Attributes
    ----------
    characters : int
        The number of characters
    labels : int
        The number of labels
    """
    UNKNOWN_WORD = 0
    PADDING = 0
    TOKEN_BEGIN = 1
    TOKEN_END = 2
    PREV_TOKEN = 3
    NEXT_TOKEN = 4
    UNK_CHAR = 11

    def __init__(self, directory, words_model_file=None, words_list=None):
        self._character_to_id = {
            'PADDING': Vocabulary.PADDING,
            'TOKEN_BEGIN': 1,
            'TOKEN_END': 2,
            'PREV_TOKEN': 3,
            'NEXT_TOKEN': 4,
            'SEGMENT_BEGIN': 5,
            'SEGMENT_END': 6,
            '\n': 7,
            '\t': 8,
            ' ': 9,
            'IDENTIFIER': 10,
            'UNK': 11
        }
        self.characters = len(self._character_to_id)
        self._label_to_id = {
            'B': 1,
            'I': 0,
            'O': 0
        }
        self._id_to_label = ['I', 'B']
        self.labels = len(self._label_to_id)
        self._word_to_id = {
            'UNKNOWN': 0
        }
        self._word_vectors = None

        import tensorflow as tf
        with tf.io.gfile.GFile(os.path.join(directory, 'characters.txt'), 'r') as f:
            for char in f:
                self._character_to_id[char[:-1]] = len(self._character_to_id)
            self.characters = len(self._character_to_id)

        if words_model_file is not None:
            self._word_vectors = []
            with tf.io.gfile.GFile(words_model_file, 'r') as f:
                for line in f:
                    split = line.split()
                    if len(split) == 2:
                        self._word_vectors.append(np.zeros(int(split[1]), dtype='float32'))
                    else:
                        word = split[0]
                        word_id = len(self._word_vectors)
                        self._word_to_id[word] = word_id
                        self._word_vectors.append(np.asarray(split[1:], dtype='float32'))

            self._word_vectors = np.vstack(self._word_vectors)
            self.words = self._word_vectors.shape[0]
        elif words_list is not None:
            with tf.io.gfile.GFile(words_list, 'r') as f:
                for identifier, line in enumerate(f, 1):
                    self._word_to_id[line[:-1]] = identifier
            self.words = len(self._word_to_id)

    @property
    def word_vectors(self):
        return self._word_vectors

    def get_word_dimension(self) -> int:
        """Gets the dimensionality of the word embeddings.

        Returns
        -------
        int
        """
        return self._word_vectors.shape[-1]

    def get_word_id(self, token_text, is_identifier=False):
        """Takes a word and gets its word embedding after performing pre-processing.

        Parameters
        ----------
        token_text : str
        is_identifier : boolean

        Returns
        -------
        int
        """
        word = re.sub(r'[^A-Za-z0-9]', ' ', token_text)
        word = word.lower()
        word = word.replace('1', 'one')
        word = word.replace('2', 'two')
        word = word.replace('3', 'three')
        word = word.replace('4', 'four')
        word = word.replace('5', 'five')
        word = word.replace('6', 'six')
        word = word.replace('7', 'seven')
        word = word.replace('8', 'eight')
        word = word.replace('9', 'nine')
        word = word.replace('0', 'zero')
        if not word.isspace() and not is_identifier:
            word_id = self._word_to_id.get(word, 0)
        else:
            word_id = 0
        return word_id

    def label_id_not_padding(self, label_id: int) -> bool:
        """Checks if a label id is any id except padding.

        Parameters
        ----------
        label_id : int

        Returns
        -------
        bool
            True if it is not padding, False if it is padding
        """
        return label_id != self._label_to_id['PADDING']

    def get_label(self, label_id: int) -> Optional[AnyStr]:
        """Gets the label string for a label id.

        Parameters
        ----------
        label_id : int
            the label id

        Returns
        -------
        str
        """
        return self._id_to_label[label_id] if label_id < len(self._id_to_label) else None

    def get_character_id(self, character: AnyStr) -> int:
        """Gets a character id for a character.

        Parameters
        ----------
        character: str
            string containing only the character or a string for a special character

        Returns
        -------
        int
        """
        return self._character_to_id.get(character, 11)

    def get_label_id(self, label: AnyStr) -> int:
        """Gets a label id for a label string.

        :param label: the label string
        :return: the identifier for the label string
        """
        return self._label_to_id[label]


def write_words(word_model, output_file):
    """Writes the words from a .vec file to an output file of strings.

    Parameters
    ----------
    word_model : str
        path to word model file
    output_file : str
        path to output file

    Returns
    -------
    None
    """
    from tensorflow.python.lib.io.file_io import FileIO
    with FileIO(word_model, 'r') as input_vectors, FileIO(output_file, 'w') as output:
        for line in input_vectors:
            split = line.split()
            if len(split) > 2:
                word = split[0]
                output.write(word)
                output.write("\n")
