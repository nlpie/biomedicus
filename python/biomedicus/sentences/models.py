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
from abc import ABCMeta, abstractmethod

import argparse
import numpy
import numpy as np
import tensorflow as tf
from argparse import ArgumentParser, Namespace
from typing import Union, AnyStr, Iterable, Tuple, List, Optional

from biomedicus.sentences.vocabulary import Vocabulary, TokenSequenceGenerator
from biomedicus.tokenization import Token, tokenize
from biomedicus.utils import pad_to_length





class SentenceModel(metaclass=ABCMeta):
    """Base class for a sentence model

    Attributes
    ----------
    session: tf.Session
        The tensorflow session.
    graph: tf.Graph
        The tensorflow graph.

    """

    def __init__(self):
        self.session = tf.Session()
        self.graph = tf.get_default_graph()

    @property
    @abstractmethod
    def model(self) -> tf.keras.models.Model:
        raise NotImplementedError

    @abstractmethod
    def compile_model(self, optimizer):
        raise NotImplementedError

    def predict_txt(self,
                    txt: AnyStr,
                    batch_size: int,
                    input_mapper: 'InputMapper',
                    tokens: Optional[List[Token]] = None,
                    include_tokens: bool = True) -> List['Sentence']:
        if tokens is None:
            tokens = list(tokenize(txt))

        if len(tokens) == 0:
            return []

        inputs, _, weights = input_mapper.map_input([(txt, tokens)], include_labels=False)
        with self.graph.as_default(), self.session.as_default():
            outputs, _ = self.model.predict(inputs, batch_size=batch_size)
        outputs = np.rint(outputs)
        not_padding = np.nonzero(weights)
        outputs = ['B' if x == 1 else 'I' for x in outputs[not_padding]]

        # construct results list
        results = []
        prev = None
        sentence = None
        for token, label in zip(tokens, outputs):
            if (label == 'B') or (label == 'O' and (prev is None or prev[1] != 'O')):
                if sentence is not None:
                    sentence.end_index = prev[0].end_index  # prev token end
                    results.append(sentence)

                sentence = Sentence(
                    start_index=token.start_index,
                    end_index=-1,
                    category='S' if label is 'B' else 'U',
                    tokens=None
                )
                if include_tokens:
                    sentence.tokens = []

            if include_tokens:
                sentence.tokens.append(token)

            prev = token, label

        if sentence is not None:
            sentence.end_index = prev[0].end_index  # prev token end
            results.append(sentence)
        return results


class BiLSTMSentenceModel(SentenceModel):
    """A sentence detector that does sequence detection using a character representation of words
    and/or a word embeddings passed to a bidirectional LSTM, which creates a
    contextual word representation before passing it dense NN layer for prediction.

    """

    @property
    def model(self) -> tf.keras.models.Model:
        return self._model

    def compile_model(self,
                      optimizer: Union[AnyStr, tf.keras.optimizers.Optimizer]):
        self.model.compile(optimizer=optimizer,
                           )

    def get_config(self):
        config = dict(self.__dict__)
        config.pop('vocabulary')
        config.pop('labels')
        config.pop('chars')
        config.pop('words')
        config.pop('word_embeddings')
        config.pop('_model')
        return config


def ensemble_hparams_parser():
    parser = argparse.ArgumentParser(add_help=False, parents=[deep_hparams_parser()])
    parser.add_argument("--base-weights-file",
                        help="The weights file for the already trained sentence model.")
    return parser


class MultiSentenceModel(BiLSTMSentenceModel):
    """The ensemble sentence model.

    """

    def __init__(self, vocabulary: Vocabulary, args):
        """Creates a new ensemble sentence model.

        Parameters
        ----------
        vocabulary: Vocabulary
            The vocabulary object.
        model_a: BiLSTMSentenceModel
            Already trained sentence model
        kwargs: dict
            All the parameters for BiLSTMSentenceModel
        """
        self.model_a = BiLSTMSentenceModel(vocabulary, args)
        if args.base_weights_file:
            self.model_a.model.load_weights(args.base_weights_file)
        super().__init__(vocabulary, args)

    def _build_model(self):
        inputs, context = self.build_layers()
        self.model_a.model.trainable = False
        _, a_context = self.model_a.model(inputs)

        context_sum = tf.keras.layers.Add()([a_context, context])

        context_sum = tf.keras.layers.BatchNormalization(
            name='corrected_word_representation'
        )(context_sum)

        logits = tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(1,
                                  activation='sigmoid',
                                  kernel_regularizer=tf.keras.regularizers.l1()),
            name='logits'
        )(context_sum)

        return tf.keras.models.Model(inputs=inputs, outputs=[logits, context_sum])

    def compile_model(self, optimizer):
        self.model.compile(optimizer=optimizer,
                           sample_weight_mode='temporal',
                           loss={
                               'logits': 'binary_crossentropy',
                               'corrected_word_representation': None
                           },
                           weighted_metrics={
                               'logits': ['binary_accuracy']
                           },
                           loss_weights={
                               'logits': 1.,
                               'corrected_word_representation': 0
                           })


class SavedModel(SentenceModel):
    def __init__(self, model_file):
        super().__init__()
        with self.graph.as_default(), self.session.as_default():
            self._model = tf.keras.models.load_model(model_file, compile=False)
            print(self._model.summary())

    @property
    def model(self) -> tf.keras.models.Model:
        return self._model

    def compile_model(self, optimizer):
        pass


class Sentence:
    def __init__(self, start_index: float, end_index: float, category: Optional[str],
                 tokens: Optional[List[Token]]):
        self.start_index = start_index
        self.end_index = end_index
        self.category = category
        self.tokens = tokens
