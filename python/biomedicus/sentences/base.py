from abc import ABCMeta, abstractmethod
from typing import Tuple, AnyStr, List, Iterable

import tensorflow as tf

from ..tokenization import Token


class SentenceModel(object, metaclass=ABCMeta):
    """Base class for a sentence model

    """

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    @property
    @abstractmethod
    def model(self) -> tf.keras.models.Model:
        pass

    @abstractmethod
    def compile_model(self, optimizer):
        pass

    @abstractmethod
    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        pass
