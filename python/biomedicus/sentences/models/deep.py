from argparse import ArgumentParser
from typing import AnyStr, List, Union, Tuple, Iterable

import numpy
import tensorflow as tf

from biomedicus.sentences.vocabulary import TokenSequenceGenerator, Vocabulary
from biomedicus.tokenization import Token
from biomedicus.utils import pad_to_length


def deep_hparams_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--sequence-length', type=int, default=32,
                        help="number of words per sequence.")
    parser.add_argument('--use-chars', type=bool, default=True,
                        help="whether to use the character model.")
    parser.add_argument('--word-length', type=int, default=32,
                        help="number of characters per word.")
    parser.add_argument('--dim-char', type=int, default=30,
                        help="length of learned char embeddings.")
    parser.add_argument('--use-token-boundaries', type=bool, default=True,
                        help="whether to insert characters representing the begin and ends of "
                             "words.")
    parser.add_argument('--use-neighbor-boundaries', type=bool, default=True,
                        help="whether to insert characters representing the end of the "
                             "previous neighbor and the begin of the next neighbor token. ")
    parser.add_argument('--use-sequence-boundaries', type=bool, default=True,
                        help="whether to insert characters representing the begin of a "
                             "segment (piece of text whose boundaries are guaranteed to "
                             "not have a sentence spanning).")
    parser.add_argument('--char-mode', choices=['cnn', 'lstm'], default='cnn',
                        help="the method to use for character representations. either 'cnn' "
                             "for convolutional neural networks or 'lstm' for a bidirectional "
                             "lstm.")
    parser.add_argument('--char-cnn-filters', type=int, default=100,
                        help="the number of cnn character filters. if "
                             "concatenate_words_chars = False then this"
                             "parameter is ignored and dim_word is used.")
    parser.add_argument('--char-cnn-kernel-size', type=int, default=4,
                        help="the kernel size (number of character embeddings to look at). ")
    parser.add_argument('--char-lstm-hidden-size', type=int, default=100,
                        help="when using bi-lstm the output dimensionality of the bi-lstm.")
    parser.add_argument('--use-words', type=bool, default=True,
                        help="whether to use word embedding word representations.")
    parser.add_argument('--lstm-hidden-size', type=int, default=300,
                        help="the number of units in the bi-lstm character layer. if "
                             "concatenate_word_chars = False then this parameter is ignored "
                             "and dim_word is used.")
    parser.add_argument('--dropout', type=float, default=.75,
                        help="the input/output dropout for the bi-lstms in the network during "
                             "training.")
    parser.add_argument('--recurrent-dropout', type=float, default=.5,
                        help="the recurrent dropout for the bi-lstms in the network.")
    parser.add_argument('--concatenate-word-chars', type=bool, default=False,
                        help="Whether to concatenate the word and character representations.")
    return parser


class BiLSTMSentenceModel:
    """A sentence detector that does sequence detection using a character representation of words
    and/or a word embeddings passed to a bidirectional LSTM, which creates a
    contextual word representation before passing it dense NN layer for prediction.

    """

    def __init__(self, vocabulary, args):
        self.vocabulary = vocabulary
        self.labels = self.vocabulary.labels
        self.chars = self.vocabulary.characters

        self.words = self.vocabulary.words
        self.word_embeddings = self.vocabulary._word_vectors
        self.dim_word = args.dim_word or self.vocabulary.get_word_dimension()

        self.sequence_length = args.sequence_length

        self.use_chars = args.use_chars

        self.word_length = args.word_length
        self.dim_char = args.dim_char

        self.use_token_boundaries = args.use_token_boundaries
        self.use_neighbor_boundaries = args.use_neighbor_boundaries
        self.use_sequence_boundaries = args.use_sequence_boundaries

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
        inputs, context = self.build_layers()

        normed = tf.keras.layers.BatchNormalization()(context)

        logits = tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(1,
                                  activation='sigmoid',
                                  kernel_regularizer=tf.keras.regularizers.l1()),
            name='logits'
        )(normed)

        return tf.keras.models.Model(inputs=inputs, outputs=[logits, context])

    def build_layers(self):
        chars_embedding = None
        char_input = None
        if self.use_chars:
            char_input = tf.keras.layers.Input(
                shape=(self.sequence_length, self.word_length),
                dtype='int32',
                name='char_input')

            char_embedding = tf.keras.layers.TimeDistributed(
                tf.keras.layers.Embedding(input_dim=self.chars,
                                          output_dim=self.dim_char,
                                          dtype='float32',
                                          mask_zero=self.char_mode == 'lstm',
                                          name='char_embedding'),
                input_shape=(self.sequence_length, self.word_length),
                name='char_embedding_distributed'
            )(char_input)

            if self.char_mode == 'cnn':
                cnn_filters = (self.char_cnn_filters if not self.concatenate_words_chars
                               else self.dim_word)
                char_cnn = tf.keras.layers.TimeDistributed(
                    tf.keras.layers.Conv1D(
                        cnn_filters,
                        self.char_cnn_kernel_size,
                        name='char_cnn'),
                    name='char_cnn_distributed'
                )(char_embedding)

                chars_embedding = tf.keras.layers.TimeDistributed(
                    tf.keras.layers.GlobalMaxPooling1D(name='char_pooling'),
                    name='char_pooling_distributed'
                )(char_cnn)
            else:
                char_lstm_hidden_size = (self.char_lstm_hidden_size
                                         if not self.concatenate_words_chars else self.dim_word)
                chars_embedding = tf.keras.layers.TimeDistributed(
                    tf.keras.layers.Bidirectional(
                        tf.keras.layers.LSTM(units=char_lstm_hidden_size,
                                             dropout=self.dropout,
                                             recurrent_dropout=self.recurrent_dropout)
                    ),
                    input_shape=(self.sequence_length, self.word_length, self.dim_char),
                    name="chars_word_embedding_distributed"
                )(char_embedding)
        if self.use_words:
            word_input = tf.keras.layers.Input(shape=(self.sequence_length,),
                                               dtype='int32',
                                               name='word_input')

            if self.word_embeddings is not None:
                word_embedding = tf.keras.layers.Embedding(input_dim=self.words,
                                                           output_dim=self.dim_word,
                                                           weights=[self.word_embeddings],
                                                           mask_zero=False,
                                                           dtype='float32',
                                                           name='word_embedding',
                                                           trainable=False)(word_input)
            else:
                word_embedding = tf.keras.layers.Embedding(input_dim=self.words,
                                                           output_dim=self.dim_word,
                                                           mask_zero=False,
                                                           dtype='float32',
                                                           name='word_embedding',
                                                           trainable=False)(word_input)
            if chars_embedding is not None:
                inputs = [char_input, word_input]

                if self.concatenate_words_chars:
                    word_embedding = tf.keras.layers.Concatenate(
                        name="word_representation"
                    )([chars_embedding, word_embedding])
                else:
                    word_embedding = tf.keras.layers.Add(
                        name="word_representation"
                    )([chars_embedding, word_embedding])

            else:
                inputs = [word_input]
                word_embedding = word_embedding

        else:
            inputs = [char_input]
            word_embedding = chars_embedding

        word_embedding = tf.keras.layers.BatchNormalization()(word_embedding)
        context = tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(self.lstm_hidden_size,
                                 return_sequences=True,
                                 dropout=self.dropout,
                                 recurrent_dropout=self.recurrent_dropout,
                                 return_state=False),
            name='contextual_word_representation'
        )(word_embedding)
        return inputs, context

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

    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool):
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
                self.txt[self.current.begin:self.current.end],
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

        if self.include_labels:
            self.labels.append(self.segment_labels)
            self.segment_labels = []
            self.weights.append(self.segment_weights)
            self.segment_weights = []

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
        begin = self.current.begin
        end = self.current.end

        all_chars = []

        if self.prev is None:
            prev_end = max(0, begin - 7)
        else:
            prev_end = max(self.prev.end, begin - 7)

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
            next_begin = min(self.next.begin, end + 7)
        else:
            next_begin = min(len(self.txt), end + 7)

        post = self.txt[end:next_begin]
        all_chars += list(post)

        if self.use_neighbor_boundaries and self.next is not None:
            all_chars.append('NEXT_TOKEN')

        # TODO: Look into doing id lookup prior to appending rather than after
        return [self.vocabulary.get_character_id(i) for i in all_chars]
