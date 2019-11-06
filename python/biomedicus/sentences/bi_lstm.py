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
from argparse import ArgumentParser

import tensorflow as tf
from tensorflow.keras.layers import BatchNormalization, Bidirectional, Conv1D, Dense, Embedding, \
    GlobalMaxPooling1D, Input, Layer, LSTM, TimeDistributed
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.regularizers import l1
from tensorflow_text import WhitespaceTokenizer


def bi_lstm_hparams_parser():
    parser = ArgumentParser(add_help=False)
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


def build_sentences_model():
    inputs, context = build_layers()

    normed = BatchNormalization()(context)

    logits = TimeDistributed(Dense(1, activation='sigmoid', kernel_regularizer=l1()),
                             name='logits'
                             )(normed)

    return Model(inputs=inputs, outputs=[logits, context])


def build_layers(hparams, vocabulary):
    chars_embedding = None
    char_input = None
    if hparams.use_chars:
        char_input = Input(shape=(None, hparams.word_length),
                           dtype='int32',
                           name='char_input')

    if hparams.use_words:
        word_input = Input(shape=(None,),
                           dtype='int32',
                           name='word_input')

        if self.word_embeddings is not None:
            word_embedding = Embedding(input_dim=vocabulary.words,
                                       output_dim=hparams.dim_word,
                                       weights=[vocabulary._word_vectors],
                                       mask_zero=False,
                                       dtype='float32',
                                       name='word_embedding',
                                       trainable=False)(word_input)
        else:
            word_embedding = Embedding(input_dim=self.words,
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

    word_embedding = BatchNormalization()(word_embedding)
    context = tf.keras.layers.Bidirectional(
        tf.keras.layers.LSTM(self.lstm_hidden_size,
                             return_sequences=True,
                             dropout=self.dropout,
                             recurrent_dropout=self.recurrent_dropout,
                             return_state=False),
        name='contextual_word_representation'
    )(word_embedding)
    return inputs, context


def build_char_model(hparams):
    model = Sequential()
    model.add(Embedding(input_dim=hparams.chars,
                        output_dim=hparams.dim_char,
                        dtype='float32',
                        mask_zero=hparams.char_mode == 'lstm',
                        name='char_embedding'))

    if hparams.char_mode == 'cnn':
        cnn_filters = (hparams.char_cnn_filters if not hparams.concatenate_words_chars
                       else hparams.dim_word)
        model.add(Conv1D(cnn_filters,
                         hparams.char_cnn_kernel_size,
                         name='char_cnn'))
        model.add(GlobalMaxPooling1D(name='char_pooling'))
    else:
        char_lstm_hidden_size = (hparams.char_lstm_hidden_size
                                 if not hparams.concatenate_words_chars else hparams.dim_word)
        model.add(Bidirectional(LSTM(units=char_lstm_hidden_size,
                                     dropout=hparams.dropout,
                                     recurrent_dropout=hparams.recurrent_dropout)))
    return model


class WhitespaceTokenizationWithOffsets(Layer):
    def __init__(self):
        super().__init__()
        self.tokenizer = WhitespaceTokenizer()

    def call(self, inputs, **kwargs):
        tokens, starts, ends = self.tokenizer.tokenize_with_offsets(inputs)
        return [tokens, starts, ends]


class InputMapper(Layer):
    def __init__(self, word_length):
        super().__init__()
        self.word_length = word_length

    def call(self, inputs, **kwargs):
        text, words, begins, ends = inputs
        padded_words = tf.concat()
