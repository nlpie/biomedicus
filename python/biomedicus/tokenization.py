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
from typing import Iterable, NamedTuple, Optional, AnyStr

Token = NamedTuple('Token',
                   [('segment', int),
                    ('start_index', int),
                    ('end_index', int),
                    ('label', Optional[int]),
                    ('is_identifier', Optional[bool]),
                    ('has_space_after', bool)])
Token.__doc__ = '''A Token in text.'''
Token.segment.__doc__ = "int: the index of the segment of text the token is in"
Token.start_index.__doc__ = "int: the start index of the token (inclusive)"
Token.end_index.__doc__ = "int: the end index of the token (exclusive)"
Token.label.__doc__ = "optional int: the end index of the token"
Token.is_identifier.__doc__ = \
    "optional bool: optional boolean specifying the token is an identifier / named entity"
Token.has_space_after.__doc__ = "bool: boolean specifying if the token has a space following it."

_segment_pattern = re.compile(r"\n{2,}|\Z", re.M)
_token_pattern = re.compile(r"(^=+$)|(^-+$)|[A-Za-z]+|\S", re.M)
_whitespace_pattern = re.compile(r"\S+")


def detect_space_after(txt: AnyStr, end: int):
    """Given text and an end index returns True if there is a space after the end index, false
    otherwise.

    Parameters
    ----------
    txt : str
        the text itself.
    end : int
        the end index of the token.

    Returns
    -------
    bool
        true if there is a space after the end index, false otherwise.
    """
    return end < len(txt) and not txt[end:end + 1].isspace()


def tokenize(txt: str) -> Iterable[Token]:
    """Tokens text according to word-embedding tokenization rules: splits on whitespace, splits on
    punctuation and numerals, keeps lines consisting entirely of "=" or "-" together.

    Parameters
    ----------
    txt: str
        the text to tokenize

    Returns
    -------
    iterable of Token
        iterable of all the tokens in the text
    """
    for token in _whitespace_pattern.finditer(txt):
        has_space_after = txt[token.end():token.end() + 1].isspace() if token.end() < len(
            txt) else False
        yield Token(0,
                    token.start(),
                    token.end(),
                    None,
                    None,
                    has_space_after)
