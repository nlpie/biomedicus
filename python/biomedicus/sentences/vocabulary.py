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
from pathlib2 import Path


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


character_to_id = {
    'PADDING': Vocabulary.PADDING,
    'TOKEN_BEGIN': Vocabulary.TOKEN_BEGIN,
    'TOKEN_END': Vocabulary.TOKEN_END,
    'PREV_TOKEN': Vocabulary.PREV_TOKEN,
    'NEXT_TOKEN': Vocabulary.NEXT_TOKEN,
    '\n': 7,
    '\t': 8,
    ' ': 9
}


def load_char_mapping(tokens_file):
    char_mappings = dict(character_to_id)
    with Path(tokens_file).open('r') as f:
        for char in f:
            char_mappings[char] = len(char_mappings)
    return char_mappings
