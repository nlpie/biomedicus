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
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import Add, BatchNormalization, Bidirectional, Concatenate, Conv1D, \
    Dense, Embedding, GlobalMaxPooling1D, Input, LSTM, TimeDistributed
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.regularizers import l1

from biomedicus.sentences.data import load_test_data
from biomedicus.sentences.train import training_parser, train_model, evaluate as eval
from biomedicus.sentences.vocabulary import load_char_mapping
from biomedicus.utilities.embeddings import load_vectors, load_words


def bi_lstm_hparams_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--embeddings', type=Path)
    parser.add_argument('--chars-file', type=Path)
    parser.add_argument('--use-chars', type=bool, default=True,
                        help="whether to use the character model.")
    parser.add_argument('--word-length', type=int, default=32,
                        help="number of characters per word.")
    parser.add_argument('--dim-char', type=int, default=30,
                        help="length of learned char embeddings.")
    parser.add_argument('--dim-word')
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
    parser.add_argument('--lstm-hidden-size', type=int, default=200,
                        help="the number of units in the bi-lstm character layer. if "
                             "concatenate_word_chars = False then this parameter is ignored "
                             "and dim_word is used.")
    parser.add_argument('--dropout', type=float, default=.5,
                        help="the input/output dropout for the bi-lstms in the network during "
                             "training.")
    parser.add_argument('--recurrent-dropout', type=float, default=.5,
                        help="the recurrent dropout for the bi-lstms in the network.")
    parser.add_argument('--concatenate-words-chars', type=bool, default=False,
                        help="Whether to concatenate the word and character representations.")
    return parser


def build_sentences_model(hparams, word_embeddings, char_mapping):
    inputs, context = build_layers(hparams, word_embeddings, char_mapping)
    normed = BatchNormalization()(context)
    logit_layer = TimeDistributed(Dense(1, activation='sigmoid', kernel_regularizer=l1()),
                                  name='logits')
    logits = tf.squeeze(logit_layer(normed), -1)

    return Model(inputs=inputs, outputs=[logits])


def build_layers(hparams, word_embeddings, char_mapping):
    character_ids = Input(shape=[None, None], dtype=tf.int64, name='character_ids')
    word_ids = Input(shape=[None], dtype=tf.int64, name='word_ids')
    dim_word = word_embeddings.shape[1] if word_embeddings is not None else hparams.dim_word
    chars_embedding = None
    if hparams.use_chars:
        model = TimeDistributed(build_char_model(hparams, char_mapping, dim_word))
        chars_embedding = model(character_ids)
    if hparams.use_words:
        word_embedding_layer = Embedding(input_dim=word_embeddings.shape[0],
                                         output_dim=dim_word,
                                         weights=[word_embeddings],
                                         mask_zero=True,
                                         dtype=tf.float32,
                                         name='word_embedding',
                                         trainable=True)
        word_representation = word_embedding_layer(word_ids)
        if chars_embedding is not None:
            word_representation_layer = (Concatenate(name="word_representation")
                                         if hparams.concatenate_words_chars
                                         else Add(name="word_representation"))
            word_representation = word_representation_layer([chars_embedding, word_representation])
            inputs = [character_ids, word_ids]
        else:
            word_representation = word_representation
            inputs = [word_ids]
    else:
        word_representation = chars_embedding
        inputs = [character_ids]

    word_representation = BatchNormalization()(word_representation)
    context_layer = Bidirectional(LSTM(hparams.lstm_hidden_size,
                                       return_sequences=True,
                                       dropout=hparams.dropout,
                                       recurrent_dropout=hparams.recurrent_dropout,
                                       return_state=False),
                                  name='contextual_word_representation')
    context = context_layer(word_representation)
    return inputs, context


def build_char_model(hparams, char_mapping, dim_word):
    model = Sequential(name='character_level_model')
    model.add(Embedding(input_dim=len(char_mapping),
                        output_dim=hparams.dim_char,
                        dtype=tf.float32,
                        mask_zero=True,
                        name='char_embedding'))
    if hparams.char_mode == 'cnn':
        cnn_filters = hparams.char_cnn_filters if hparams.concatenate_words_chars else dim_word
        model.add(Conv1D(cnn_filters,
                         hparams.char_cnn_kernel_size,
                         name='char_cnn'))
        model.add(GlobalMaxPooling1D(name='char_pooling'))
    else:
        char_lstm_hidden_size = (hparams.char_lstm_hidden_size
                                 if not hparams.concatenate_words_chars else dim_word)
        model.add(Bidirectional(LSTM(units=char_lstm_hidden_size,
                                     dropout=hparams.dropout,
                                     recurrent_dropout=hparams.recurrent_dropout),
                                merge_mode='sum'))
    return model


def train(conf):
    words, vectors = load_vectors(conf.embeddings)
    vectors = np.array(vectors)
    char_mappings = load_char_mapping(conf.chars_file)

    model = build_sentences_model(conf, vectors, char_mappings)
    train_model(model, conf)


def print_model(conf):
    words, vectors = load_vectors(conf.embeddings)
    vectors = np.array(vectors)
    char_mappings = load_char_mapping(conf.chars_file)

    model = build_sentences_model(conf, vectors, char_mappings)
    tf.keras.utils.plot_model(model, conf.output_file)


def evaluate(conf):
    words = load_words(conf.words_file)
    chars_mapping = load_char_mapping(conf.chars_file)
    test_data = load_test_data(conf.test_data, chars_mapping, words)
    model = tf.keras.models.load_model(conf.model_file)
    precision, recall, f1 = eval(model, test_data)
    print('precision: {} - recall: {} - f1: {}'.format(precision, recall, f1))


def main(args=None):
    parser = ArgumentParser(add_help=True)

    def _print_usage(_):
        parser.print_help()

    parser.set_defaults(func=_print_usage)

    subparsers = parser.add_subparsers()

    train_parser = subparsers.add_parser('train',
                                         parents=[training_parser(), bi_lstm_hparams_parser()])
    train_parser.set_defaults(func=train)

    print_model_parser = subparsers.add_parser('print_model', parents=[bi_lstm_hparams_parser()])
    print_model_parser.add_argument('--output-file', default='model.png')
    print_model_parser.set_defaults(func=print_model)

    evaluate_parser = subparsers.add_parser('evaluate')
    evaluate_parser.add_argument('--model-file', required=True)
    evaluate_parser.add_argument('--test-data', required=True)
    evaluate_parser.add_argument('--words-file', required=True)
    evaluate_parser.add_argument('--chars-file', required=True)
    evaluate_parser.set_defaults(func=evaluate)

    conf = parser.parse_args(args)
    conf.func(conf)


if __name__ == "__main__":
    main()
