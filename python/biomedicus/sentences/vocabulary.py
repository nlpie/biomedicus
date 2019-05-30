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

    def __init__(self, directory, words_model_file=None, words_list=None):
        self._character_to_id = {
            'PADDING': 0,
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


def _split_token_line(txt: AnyStr, line: Optional[str]) -> Optional[Token]:
    """Internal method for splitting token lines from the .labels format.
    """
    if not line:
        return None

    split = line.split()

    if len(split) < 5:
        return None

    segment = int(split[0])
    begin = int(split[1])
    end = int(split[2])
    label = split[3]
    is_identifier = split[4] == '1'
    space_after = detect_space_after(txt, end)
    return Token(segment, begin, end, label, is_identifier, space_after)


def directory_labels_generator(directory: AnyStr,
                               repeat=False,
                               return_name=False) -> Iterable[Tuple[AnyStr, List[Token]]]:
    """Generates text, list of tokens tuples a directory containing text and labels files. The
    labels files for each text document should contain one token on each line with the format
    [segment] [begin_index] [end_index] [label] [1 if identifier, 0 if not]

    :param directory: The directory to read the text and labels documents from
    :param repeat:
    :return:
    """
    import tensorflow as tf
    while True:
        for doc_dir, _, docs in tf.io.gfile.walk(directory):
            for doc in docs:
                if not doc.endswith('.txt'):
                    continue
                path = pathlib.PurePath(doc_dir, doc)
                print("reading document {}".format(path))
                with tf.io.gfile.GFile(str(path), 'r') as f:
                    txt = f.read()

                labels_path = path.with_suffix('.labels')
                with tf.io.gfile.GFile(str(labels_path), 'r') as f:
                    tokens = [_split_token_line(txt, x) for x in f]
                if return_name:
                    yield txt, doc, tokens
                else:
                    yield txt, tokens

        if not repeat:
            break


class TokenSequenceGenerator(ABC, Iterable):
    """Abstract base class for transforming an iterable of document-tokens into data
    usable by a classifier.
    """

    def __init__(
            self,
            input_source: Iterable[Tuple[AnyStr, List[Token]]],
            batch_size,
            sequence_length
    ):
        self.input_source = input_source
        self.batch_size = batch_size
        self.sequence_length = sequence_length

        self.batch_count = 0
        self.sequence_count = 0

        self.txt = None

        self.prev = None
        self.current = None
        self.next = None

    def __iter__(self):
        for txt, tokens in self.input_source:
            self.txt = txt

            it = iter(tokens)
            self.current = next(it, None)

            while self.current:
                self.next = next(it, None)

                self._handle_token()
                self.sequence_count += 1

                if self._sequence_full() or self._end_of_sequence():
                    self._finish_sequence()
                    self.batch_count += 1
                    self.sequence_count = 0
                    if self.batch_count == self.batch_size:
                        yield self._batch()
                        self.batch_count = 0

                self.prev = self.current
                self.current = self.next

        yield self._batch()

    def _sequence_full(self):
        return self.sequence_length == self.sequence_count

    def _end_of_sequence(self):
        return self.sequence_length > 0 and (
                not self.next or self.current.segment != self.next.segment)

    @abstractmethod
    def _handle_token(self):
        pass

    @abstractmethod
    def _finish_sequence(self):
        pass

    @abstractmethod
    def _batch(self):
        pass


def _map_to_ints(string):
    return [ord(x) for x in string]


def _strings(ints):
    return [str(x) for x in ints]


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
