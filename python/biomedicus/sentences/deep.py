from typing import Optional, AnyStr, List, Union, Tuple, Iterable

import numpy
import tensorflow as tf

from .base import SentenceModel, Main
from .vocabulary import TokenSequenceGenerator, Vocabulary
from ..tokenization import Token
from ..utils import default_value, pad_to_length


class BiLSTMSentenceModel(SentenceModel):
    """A sentence detector that does sequence detection using a character representation of words
    and/or a word embeddings passed to a bidirectional LSTM, which creates a
    contextual word representation before passing it dense NN layer for prediction.

    """

    def __init__(self,
                 vocabulary: Vocabulary,
                 dim_word: Optional[int] = None,
                 sequence_length: Optional[int] = None,
                 use_chars: Optional[bool] = None,
                 word_length: Optional[int] = None,
                 dim_char: Optional[int] = None,
                 use_token_boundaries: Optional[bool] = None,
                 use_neighbor_boundaries: Optional[bool] = None,
                 use_sequence_boundaries: Optional[bool] = None,
                 char_mode: Optional[str] = None,
                 char_cnn_filters: Optional[int] = None,
                 char_cnn_kernel_size: Optional[int] = None,
                 char_lstm_hidden_size: Optional[int] = None,
                 use_words: Optional[bool] = None,
                 lstm_hidden_size: Optional[int] = None,
                 dropout: Optional[float] = None,
                 recurrent_dropout: Optional[float] = None,
                 concatenate_words_chars: Optional[bool] = None,
                 verbose: Optional[bool] = None,
                 **_):
        """

        Parameters
        ----------
        vocabulary: Vocabulary
            vocabulary object containing information about the labels, characters, and word
            embeddings
        dim_word: int
            dimensionality of the word embeddings, by default gets from the vocabulary
        sequence_length: int
            length of sequences in number of words, by default uses 32
        use_chars: bool
            whether to augment word embeddings with character information
        word_length: int
            max length of words in number of characters, words longer than this are truncated.
            default is 32.
        dim_char: int
            the dimensionality of learned character embeddings. default is 30
        use_token_boundaries: bool
            whether to add the boundaries of tokens as special symbols to the character information.
            default is True
        use_neighbor_boundaries: bool
            whether to add the boundaries of neighbor tokens as special symbols to the character
            information. default is True.
        use_sequence_boundaries: bool
            whether to add the boundaries of the text as special symbols to the character
            information. default is True
        char_mode: str
            whether to use a bi-lstm ('lstm') or a cnn ('cnn') to create character representations.
            default is 'cnn'
        char_cnn_filters: int
            the number of cnn character filters. if concatenate_words_chars = False then this
            parameter is ignored and dim_word is used. default is 100.
        char_cnn_kernel_size: int
            the number of character embeddings each filter looks at. default is 4.
        char_lstm_hidden_size: int
            the number of units in the bi-lstm character layer. if concatenate_word_chars = False
            then this parameter is ignored and dim_word is used. default is 25
        use_words: bool
            whether to use word embeddings. default is True
        lstm_hidden_size: int
            the number of units in the bi-lstm contextual word representation layer. default is 300.
        dropout: float
            the input/output dropout for the bi-lstms in the network during training.
            default is .75.
        recurrent_dropout: float
            the recurrent dropout for the bi-lstms in the network. default is .5.
        concatenate_words_chars: bool
            Whether to concatenate the word and character representations.
            default is False = add the word and character representations
        verbose
        _
        """
        del _

        self.vocabulary = vocabulary
        self.labels = vocabulary.labels
        self.chars = vocabulary.characters

        self.words = vocabulary.words
        self.word_embeddings = vocabulary._word_vectors
        self.dim_word = dim_word or vocabulary.get_word_dimension()

        self.sequence_length = default_value(sequence_length, 32)

        self.use_chars = use_chars if use_chars is not None else True

        self.word_length = default_value(word_length, 32)
        self.dim_char = default_value(dim_char, 30)

        self.use_token_boundaries = default_value(use_token_boundaries, True)
        self.use_neighbor_boundaries = default_value(use_neighbor_boundaries, True)
        self.use_sequence_boundaries = default_value(use_sequence_boundaries, True)

        self.char_mode = default_value(char_mode, 'cnn')

        self.char_cnn_filters = default_value(char_cnn_filters, 100)
        self.char_cnn_kernel_size = default_value(char_cnn_kernel_size, 4)

        self.char_lstm_hidden_size = default_value(char_lstm_hidden_size, 25)

        self.use_words = default_value(use_words, True)

        self.lstm_hidden_size = default_value(lstm_hidden_size, 300)

        self.dropout = default_value(dropout, .75)
        self.recurrent_dropout = default_value(recurrent_dropout, .5)
        self.verbose = default_value(verbose, True)

        self.concatenate_words_chars = default_value(concatenate_words_chars, False)

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

    def compile_model(self, optimizer: Union[AnyStr, tf.keras.optimizers.Optimizer]):
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
            label_id = self.vocabulary.get_label_id(self.current.label)
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


class DeepMain(Main):
    def add_args(self, parser):
        parser.add_argument('--sequence-length', type=int,
                            help="number of words per sequence. defaults to to 32.")
        parser.add_argument('--use-chars', type=bool,
                            help="whether to use the character model. defaults to True")
        parser.add_argument('--word-length', type=int,
                            help="number of characters per word. defaults to 32.")
        parser.add_argument('--dim-char', type=int,
                            help="length of learned char embeddings. default is 30.")
        parser.add_argument('--use-token-boundaries', type=bool,
                            help="whether to insert characters representing the begin and ends of "
                                 "words. default is True")
        parser.add_argument('--use-neighbor-boundaries', type=bool,
                            help="whether to insert characters representing the end of the "
                                 "previous neighbor and the begin of the next neighbor token. "
                                 "default is True")
        parser.add_argument('--use-sequence-boundaries', type=bool,
                            help="whether to insert characters representing the begin of a "
                                 "segment (piece of text whose boundaries are guaranteed to "
                                 "not have a sentence spanning). default is True")
        parser.add_argument('--char-mode', choices=['cnn', 'lstm'],
                            help="the method to use for character representations. either 'cnn' "
                                 "for convolutional neural networks or 'lstm' for a bidirectional "
                                 "lstm. default is 'cnn'.")
        parser.add_argument('--char-cnn-filters', type=int,
                            help="the number of cnn character filters. if "
                                 "concatenate_words_chars = False then this"
                                 "parameter is ignored and dim_word is used. default is 100. ")
        parser.add_argument('--char-cnn-kernel-size', type=int,
                            help="the kernel size (number of character embeddings to look at). "
                                 "default is 4.")
        parser.add_argument('--char-lstm-hidden-size', type=int,
                            help="when using bi-lstm the output dimensionality of the bi-lstm. "
                                 "default is 25.")
        parser.add_argument('--use-words', type=bool,
                            help="whether to use word embedding word representations. default is "
                                 "True.")
        parser.add_argument('--lstm-hidden-size', type=int,
                            help="the number of units in the bi-lstm character layer. if "
                                 "concatenate_word_chars = False then this parameter is ignored "
                                 "and dim_word is used. default is 25")
        parser.add_argument('--dropout', type=float,
                            help="the input/output dropout for the bi-lstms in the network during "
                                 "training. default is .75.")
        parser.add_argument('--recurrent-dropout', type=float,
                            help="the recurrent dropout for the bi-lstms in the network. "
                                 "default is .5.")
        parser.add_argument('--concatenate-word-chars', type=bool,
                            help="Whether to concatenate the word and character representations. "
                                 "default is False = add the word and character representations ")

    def get_model(self, vocabulary, **kwargs) -> 'SentenceModel':
        return BiLSTMSentenceModel(vocabulary=vocabulary, **kwargs)


if __name__ == '__main__':
    DeepMain().main()
