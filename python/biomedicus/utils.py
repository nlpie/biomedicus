from __future__ import absolute_import

from typing import TypeVar, Optional

import numpy as np

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
