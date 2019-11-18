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
import tensorflow_text
from tensorflow.keras.layers import Add, BatchNormalization, Bidirectional, Concatenate, Conv1D, \
    Dense, Embedding, GlobalMaxPooling1D, Input, Layer, LSTM, TimeDistributed
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.regularizers import l1

from biomedicus.sentences.train import training_parser
from biomedicus.sentences.vocabulary import Vocabulary


def bi_lstm_hparams_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--use-chars', type=bool, default=True,
                        help="whether to use the character model.")
    parser.add_argument('--word-length', type=int, default=32,
                        help="number of characters per word.")
    parser.add_argument('--dim-char', type=int, default=30,
                        help="length of learned char embeddings.")
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
    parser.add_argument('--dropout', type=float, default=.5,
                        help="the input/output dropout for the bi-lstms in the network during "
                             "training.")
    parser.add_argument('--recurrent-dropout', type=float, default=.5,
                        help="the recurrent dropout for the bi-lstms in the network.")
    parser.add_argument('--concatenate-word-chars', type=bool, default=False,
                        help="Whether to concatenate the word and character representations.")
    return parser


def build_sentences_model(hparams, word_embeddings, char_mapping, words_file):
    inputs, context = build_layers(hparams, word_embeddings, char_mapping, words_file)
    normed = BatchNormalization()(context)
    logit_layer = TimeDistributed(Dense(1, activation='sigmoid', kernel_regularizer=l1()),
                                  name='logits')
    logits = logit_layer(normed)

    return Model(inputs=inputs, outputs=[logits, context])


def build_layers(hparams, word_embeddings, char_mapping, words_file):
    priors = Input(shape=[None], dtype=tf.string, name='priors')
    tokens = Input(shape=[None], dtype=tf.string, name='tokens')
    posts = Input(shape=[None], dtype=tf.string, name='posts')

    inputs = [priors, tokens, posts]

    chars_embedding = None
    if hparams.use_chars:
        char_mapping_layer = CharacterRepresentation(char_mapping)
        char_ids = char_mapping_layer(inputs)
        model = build_char_model(hparams)
        chars_embedding = model(char_ids)
    if hparams.use_words:
        word_lookup_layer = WordLookup(words_file)
        word_ids = word_lookup_layer(tokens)

        if word_embeddings is not None:
            word_embedding_layer = Embedding(input_dim=word_embeddings.shape[0],
                                             output_dim=word_embeddings.shape[1],
                                             weights=[word_embeddings],
                                             mask_zero=False,
                                             dtype='float32',
                                             name='word_embedding',
                                             trainable=False)
        else:
            with open(words_file, 'r') as f:
                words = len(f.readlines())
            word_embedding_layer = Embedding(input_dim=words,
                                             output_dim=hparams.dim_word,
                                             mask_zero=False,
                                             dtype='float32',
                                             name='word_embedding',
                                             trainable=True)
        word_embedding = word_embedding_layer(word_ids)
        if chars_embedding is not None:
            word_representation_layer = (Concatenate(name="word_representation")
                                         if hparams.concatenate_word_chars
                                         else Add(name="word_representation"))
            word_embedding = word_representation_layer([chars_embedding, word_embedding])
        else:
            word_embedding = word_embedding
    else:
        word_embedding = chars_embedding

    word_embedding = BatchNormalization()(word_embedding)
    context_layer = Bidirectional(LSTM(hparams.lstm_hidden_size,
                                       return_sequences=True,
                                       dropout=hparams.dropout,
                                       recurrent_dropout=hparams.recurrent_dropout,
                                       return_state=False),
                                  name='contextual_word_representation')
    context = context_layer(word_embedding)
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


class WordLookup(Layer):
    def __init__(self, words_file):
        super().__init__()
        self.table = tf.lookup.StaticHashTable(
            tf.lookup.TextFileInitializer(
                words_file,
                tf.string,
                tf.lookup.TextFileIndex.WHOLE_LINE,
                tf.int64,
                tf.lookup.TextFileIndex.LINE_NUMBER
            ),
            Vocabulary.UNKNOWN_WORD
        )

    def call(self, tokens, **kwargs):
        normed = tensorflow_text.case_fold_utf8(tokens)
        normed = tf.strings.regex_replace(normed, "[\\pP\\pS]", "")
        normed = tf.strings.regex_replace(normed, "\\pN", "#")
        return self.table.lookup(normed, Vocabulary.UNKNOWN_WORD)


class CharacterRepresentation(Layer):
    """Constructs tokens for the character representation of words.

    The tokens contain the following information concatenated:
    - Marker for previous token
    - Whitespace characters after the previous token and before this token
    - Marker for start of this token
    - This token's characters
    - Marker for the end of this token
    - Whitespace characters after this token and before the next
    - Marker for the next token

    It takes an input triplet of (docs [N], starts [N, (N)], ends [N, (N)])

    """

    def __init__(self, chars_mapping, **kwargs):
        super().__init__(**kwargs)
        keys, values = zip(*chars_mapping.items())
        self.table = tf.lookup.StaticHashTable(tf.lookup.KeyValueTensorInitializer(keys, values),
                                               Vocabulary.UNK_CHAR)

    def call(self, inputs, **kwargs):
        priors, tokens, posts = inputs

        return tf.concat([
            marker_char(Vocabulary.PREV_TOKEN, tokens),
            self._lookup_char_ids(priors),
            marker_char(Vocabulary.TOKEN_BEGIN, tokens),
            self._lookup_char_ids(tokens),
            marker_char(Vocabulary.TOKEN_END, tokens),
            self._lookup_char_ids(posts),
            marker_char(Vocabulary.NEXT_TOKEN, tokens)
        ], axis=-1)

    def _lookup_char_ids(self, chars):
        return tf.ragged.map_flat_values(self.table.lookup,
                                         tf.strings.unicode_split(chars, 'UTF-8'))


def doc_substrs(docs, starts, ends):
    lens = ends - starts
    return tf.RaggedTensor.from_tensor(tf.strings.substr(tf.expand_dims(docs, -1),
                                                         starts.to_tensor(),
                                                         lens.to_tensor()),
                                       ends.row_lengths())


def marker_char(int_value, like):
    return tf.RaggedTensor.from_row_lengths(tf.fill(like.flat_values.shape,
                                                    tf.cast(int_value, tf.int32)),
                                            like.row_lengths())


def train(conf):
    pass


def main(args=None):
    parser = ArgumentParser(add_help=True, parents=[bi_lstm_hparams_parser()])
    subparsers = parser.add_subparsers()

    train_parser = subparsers.add_parser('train', parents=[training_parser()])
    train_parser.set_defaults(func=train)

    conf = parser.parse_args(args)
    conf.func(conf)


if __name__ == "__main__":
    main()
