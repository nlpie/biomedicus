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
import numpy as np
from typing import TypeVar, Optional

__all__ = ['default_value', 'pad_to_length']  # don't include type var T

T = TypeVar('T')


def default_value(existing: Optional[T], default: T) -> T:
    """Used for providing a default value for a None-valued parameter

    Parameters
    ----------
    existing
        the parameter value, either a true value or None to use the default
    default
        a default value to use if the parameter is None

    Returns
    -------
    any
        a value for a setting

    """
    if existing is None:
        return default
    return existing


def pad_to_length(sequences, length, value=0):
    """Pads sequences to being the same length, truncating right if they are longer.

    Attributes
    ----------
    sequences
        the sequences to pad
    length : int
        the length to pad to
    value
        the value to use to pad

    Returns
    -------
    numpy.ndarray
        The padding sequences

    """
    result = []

    for seq in sequences:
        if len(seq) > length:
            seq = seq[:length]

        instance = [value for _ in range(length)]
        instance[:len(seq)] = seq
        result.append(instance)

    return np.array(result)
