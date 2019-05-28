from abc import ABCMeta, abstractmethod
from typing import Tuple, AnyStr, List, Iterable, Optional, Dict

import numpy as np
import tensorflow as tf

from biomedicus.tokenization import Token, tokenize


class SentenceModel(object, metaclass=ABCMeta):
    """Base class for a sentence model

    """
    @property
    @abstractmethod
    def model(self) -> tf.keras.models.Model:
        raise NotImplementedError

    @abstractmethod
    def compile_model(self, optimizer):
        raise NotImplementedError

    @abstractmethod
    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        raise NotImplementedError

    def predict_txt(self,
                    txt: AnyStr,
                    batch_size: int,
                    tokens: Optional[List[Token]] = None,
                    include_tokens: bool = True) -> List[Dict]:
        """Takes input text, tokenizes it, and then returns a list of tokens with labels

        Attributes
        ----------
        txt : str
            the text to predict sentences
        tokens : iterable of Token
            tokens if the text has already been tokenized
        include_tokens : bool
            whether the result sentences should include their tokens

        Returns
        -------
        list
            a list of lists of tokens with their sentence classifications. Each list is a sentence.
        """
        if tokens is None:
            tokens = list(tokenize(txt))

        if len(tokens) == 0:
            return []

        inputs, _, weights = self.map_input([(txt, tokens)], include_labels=False)

        outputs, _ = self.model.predict(inputs, batch_size=batch_size)
        outputs = np.rint(outputs)
        not_padding = np.nonzero(weights)
        outputs = ['B' if x == 1 else 'I' for x in outputs[not_padding]]

        # construct results list
        results = []
        prev = None
        sentence = None
        for token, label in zip(tokens, outputs):
            result_token = (token.begin, token.end, token.has_space_after)
            if (label == 'B') or (label == 'O' and (prev is None or prev[1] != 'O')):
                if sentence is not None:
                    sentence['end'] = prev[0].end  # prev token end
                    results.append(sentence)

                sentence = {
                    'begin': token.begin,
                    'category': 'S' if label is 'B' else 'U'
                }
                if include_tokens:
                    sentence['tokens'] = []

            if include_tokens:
                sentence['tokens'].append(result_token)

            prev = token, label

        sentence['end'] = prev[0][2]  # prev token end
        results.append(sentence)
        return results
