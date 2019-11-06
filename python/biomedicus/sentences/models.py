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

    def __init__(self, vocabulary: Vocabulary, args: Namespace):
        super().__init__()
        self.vocabulary = vocabulary
        self.labels = self.vocabulary.labels
        self.chars = self.vocabulary.characters

        self.words = self.vocabulary.words
        self.word_embeddings = self.vocabulary.word_vectors
        self.dim_word = args.dim_word or self.vocabulary.get_word_dimension()

        self.sequence_length = args.sequence_length

        self.use_chars = args.use_chars

        self.word_length = args.word_length
        self.dim_char = args.dim_char

        self.char_mode = args.char_mode
        self.char_cnn_filters = args.char_cnn_filters
        self.char_cnn_kernel_size = args.char_cnn_kernel_size
        self.char_lstm_hidden_size = args.char_lstm_hidden_size

        self.use_words = args.use_words

        self.lstm_hidden_size = args.lstm_hidden_size

        self.dropout = args.dropout
        self.recurrent_dropout = args.recurrent_dropout

        self.concatenate_words_chars = args.concatenate_word_chars

        self._model = self._build_model()

    def _build_model(self) -> tf.keras.models.Model:


    def build_layers(self):


    @property
    def model(self) -> tf.keras.models.Model:
        return self._model

    def compile_model(self,
                      optimizer: Union[AnyStr, tf.keras.optimizers.Optimizer]):
        self.model.compile(optimizer=optimizer,
                           sample_weight_mode='temporal',
                           loss={
                               'logits': 'binary_crossentropy',
                               'contextual_word_representation': None
                           },
                           weighted_metrics={
                               'logits': ['binary_accuracy']
                           },
                           loss_weights={
                               'logits': 1.,
                               'contextual_word_representation': 0.
                           })

    def get_config(self):
        config = dict(self.__dict__)
        config.pop('vocabulary')
        config.pop('labels')
        config.pop('chars')
        config.pop('words')
        config.pop('word_embeddings')
        config.pop('_model')
        return config


class InputMapper(metaclass=ABCMeta):

    @abstractmethod
    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        raise NotImplementedError


class DeepMapper(InputMapper):
    def __init__(self, vocabulary: Vocabulary, args: Namespace):
        self.vocabulary = vocabulary

        self.sequence_length = args.sequence_length

        self.use_chars = args.use_chars

        self.word_length = args.word_length

        self.use_token_boundaries = args.use_token_boundaries
        self.use_neighbor_boundaries = args.use_neighbor_boundaries
        self.use_sequence_boundaries = args.use_sequence_boundaries

        self.use_words = args.use_words

    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        generator = InputGenerator(txt_tokens,
                                   vocabulary=self.vocabulary,
                                   sequence_length=self.sequence_length,
                                   word_length=self.word_length,
                                   use_chars=self.use_chars,
                                   use_token_boundaries=self.use_token_boundaries,
                                   use_neighbor_boundaries=self.use_neighbor_boundaries,
                                   use_sequence_boundaries=self.use_sequence_boundaries,
                                   include_labels=include_labels,
                                   use_words=self.use_words)
        inputs = next(iter(generator))
        return inputs


class InputGenerator(TokenSequenceGenerator):
    """Turns a iterable of (text, List[Token]) tuples into an iterable of input or (input, label)
    tuples
    """

    def __init__(self,
                 input_source: Iterable[Tuple[AnyStr, List[Token]]],
                 vocabulary: Vocabulary,
                 sequence_length: int,
                 word_length: int,
                 use_chars: bool,
                 use_words: bool,
                 use_token_boundaries: bool,
                 use_neighbor_boundaries: bool,
                 use_sequence_boundaries: bool,
                 include_labels: bool = True,
                 batch_size: int = -1):
        super().__init__(input_source, batch_size, sequence_length)
        self.vocabulary = vocabulary

        self.word_length = word_length

        self.use_chars = use_chars
        self.use_words = use_words
        self.use_token_boundaries = use_token_boundaries
        self.use_neighbor_boundaries = use_neighbor_boundaries
        self.use_sequence_boundaries = use_sequence_boundaries

        self.batch_count = 0
        self.chars = []
        self.words = []
        self.labels = []
        self.weights = []

        self.sequence_count = 0
        self.segment_chars = []
        self.segment_words = []
        self.segment_labels = []
        self.segment_weights = []

        self.include_labels = include_labels

        self.class_counts = {'B': 0, 'I': 0, 'O': 0}

    def _handle_token(self):
        """Turns the token into its character ids and word id and adds label to the current
        sequence.
        """
        if self.use_chars:
            chars = self.get_chars()
            self.segment_chars.append(chars)

        if self.use_words:
            word_id = self.vocabulary.get_word_id(
                self.txt[self.current.start_index:self.current.end_index],
                is_identifier=self.current.is_identifier)
            self.segment_words.append(word_id)

        if self.include_labels:
            label_id = self.vocabulary._label_to_id[self.current.label]
            self.class_counts[self.current.label] += 1
            self.segment_labels.append(label_id)
            if self.current.label == 'O':
                self.segment_weights.append(0.)
            else:
                self.segment_weights.append(1.)
        else:
            self.segment_weights.append(1.)

    def _finish_sequence(self):
        if self.use_chars:
            self.chars.append(pad_to_length(self.segment_chars,
                                            length=self.word_length,
                                            value=0))
            self.segment_chars = []

        if self.use_words:
            self.words.append(self.segment_words)
            self.segment_words = []

        self.weights.append(self.segment_weights)
        self.segment_weights = []

        if self.include_labels:
            self.labels.append(self.segment_labels)
            self.segment_labels = []

    def _batch(self):
        inputs = {}

        if self.use_chars:
            inputs['char_input'] = pad_to_length(self.chars,
                                                 length=self.sequence_length,
                                                 value=numpy.zeros(
                                                     self.word_length))
            self.chars = []
        if self.use_words:
            inputs['word_input'] = pad_to_length(
                self.words,
                length=self.sequence_length,
                value=0
            )
            self.words = []

        class_counts = self.class_counts
        self.class_counts = {'B': 0, 'I': 0, 'O': 0}
        weights = pad_to_length(
            self.weights,
            length=self.sequence_length,
            value=0.
        )
        self.weights = []

        if self.include_labels:
            labels = pad_to_length(
                self.labels,
                length=self.sequence_length,
                value=0
            )
            self.labels = []
            labels = labels[:, :, numpy.newaxis]

            return inputs, class_counts, weights, labels
        else:
            return inputs, class_counts, weights

    def get_chars(self) -> List[int]:
        begin = self.current.start_index
        end = self.current.end_index

        all_chars = []

        if self.prev is None:
            prev_end = max(0, begin - 7)
        else:
            prev_end = max(self.prev.end_index, begin - 7)

            if self.use_neighbor_boundaries:
                all_chars.append('PREV_TOKEN')

        pre = self.txt[prev_end:begin]
        all_chars += list(pre)

        if self.use_sequence_boundaries:
            if self.prev is None or self.current.segment != self.prev.segment:
                all_chars.append('SEGMENT_BEGIN')

        if self.use_token_boundaries:
            all_chars.append('TOKEN_BEGIN')

        if self.current.is_identifier:
            all_chars.append('IDENTIFIER')
        else:
            token_txt = self.txt[begin:end]
            all_chars += list(token_txt)

        if self.use_token_boundaries:
            all_chars.append('TOKEN_END')

        if self.use_sequence_boundaries:
            if self.next is None or self.current.segment != self.next.segment:
                all_chars.append('SEGMENT_END')

        if self.next is not None:
            next_begin = min(self.next.start_index, end + 7)
        else:
            next_begin = min(len(self.txt), end + 7)

        post = self.txt[end:next_begin]
        all_chars += list(post)

        if self.use_neighbor_boundaries and self.next is not None:
            all_chars.append('NEXT_TOKEN')

        # TODO: Look into doing id lookup prior to appending rather than after
        return [self.vocabulary.get_character_id(i) for i in all_chars]


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
