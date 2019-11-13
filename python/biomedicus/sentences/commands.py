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

import logging
import os
from argparse import Namespace, ArgumentParser
from typing import Any

import numpy as np
import tensorflow as tf
from mtap import run_processor, processor_parser

from biomedicus.config import load_config
from biomedicus.sentences.models import deep_hparams_parser, BiLSTMSentenceModel, DeepMapper, \
    ensemble_hparams_parser, MultiSentenceModel, SavedModel, SentenceModel, InputMapper
from biomedicus.sentences.processor import SentenceProcessor
from biomedicus.sentences.utils import build_log_name, Metrics
from biomedicus.sentences.utils import print_metrics
from biomedicus.sentences.vocabulary import directory_labels_generator, Vocabulary, write_words

logger = logging.getLogger(__name__)


class SentenceCommands(Namespace):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._vocabulary = None
        self._model = None
        self._mapper = None

    @property
    def vocabulary(self):
        if self._vocabulary is None:
            self._vocabulary = Vocabulary(self.vocab_dir, self.word_embeddings, self.words_list)
        return self._vocabulary

    def _load_model(self):
        logger.info('Creating sentences model.')
        hparams = {}
        if self.hparams is not None:
            import yaml
            try:
                from yaml import CLoader as Loader
            except ImportError:
                from yaml import Loader
            with open(self.hparams, 'rb') as f:
                hparams = yaml.load(f, Loader=Loader)
        if self.model == 'deep':
            logger.info('Using deep model.')
            p = deep_hparams_parser()
            Model = BiLSTMSentenceModel
            Mapper = DeepMapper
        elif self.model == 'ensemble':
            logger.info('Using ensemble model.')
            p = ensemble_hparams_parser()
            Model = MultiSentenceModel
            Mapper = DeepMapper
        else:
            raise ValueError('Unrecognized model: ' + self.model)

        p.set_defaults(**hparams)
        model_args = p.parse_args(self.additional_args)

        if self.model_file is not None and os.path.isfile(self.model_file):
            model = SavedModel(self.model_file)
        else:
            model = Model(self.vocabulary, model_args)

        mapper = Mapper(self.vocabulary, model_args)

        self._model = model
        self._mapper = mapper

    @property
    def sentence_model(self) -> SentenceModel:
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def mapper(self) -> InputMapper:
        if self._mapper is None:
            self._load_model()
        return self._mapper

    def run_processor(self):
        processor = self.create_processor()
        run_processor(processor, namespace=self)

    def create_processor(self):
        processor = SentenceProcessor(self.sentence_model, self.mapper)
        return processor

    def write_words(self):
        write_words(self.word_embeddings, self.words_list)

    def train_on_data(self, data, sample_weights, targets, job_dir):
        """Trains a sentence detector model on data.

        Parameters
        ----------
        data : numpy.ndarray
            input data for the model
        sample_weights : numpy.ndarray
            the weights of each sample/word
        targets : numpy.ndarray

        job_dir : str
            directory to write

        Returns
        -------
        None

        """
        log_name = build_log_name()

        callbacks = []
        metrics = Metrics(self.vocabulary)
        callbacks.append(metrics)

        if self.tensorboard:
            log_path = os.path.join(job_dir, "logs", log_name)
            tensorboard = tf.keras.callbacks.TensorBoard(log_dir=log_path)
            callbacks.append(tensorboard)

        if self.checkpoints:
            checkpoint = tf.keras.callbacks.ModelCheckpoint(
                os.path.join(job_dir, "models", log_name + ".h5"),
                verbose=1,
                save_best_only=True
            )
            callbacks.append(checkpoint)

        self.sentence_model.compile_model(optimizer=self.optimizer)

        if self.early_stopping:
            stopping = tf.keras.callbacks.EarlyStopping(patience=self.early_stopping_patience,
                                                        min_delta=self.early_stopping_delta)
            callbacks.append(stopping)

        with self.sentence_model.graph.as_default(), self.sentence_model.session.as_default():
            self.sentence_model.model.fit(data,
                                          {'logits': targets},
                                          batch_size=self.batch_size,
                                          epochs=self.epochs,
                                          sample_weight=sample_weights,
                                          validation_split=self.validation_split,
                                          callbacks=callbacks)

    def train_model(self):
        """Trains a sentence detector model using a labeled training set

        Returns
        -------
        None
        """
        labels_generator = directory_labels_generator(self.training_dir)
        data, class_counts, weights, targets = self.mapper.map_input(labels_generator,
                                                                     include_labels=True)

        if self.verbose:
            print("\nClass counts: ")
            print(class_counts)

        if self.use_class_weights:
            print(type(class_counts))
            total = class_counts['B'] + class_counts['I']
            class_weights = np.array([total / (2 * class_counts['I']),
                                      total / (2 * class_counts['B'])])

            if self.verbose:
                print("\nusing class weights: %s" % class_weights)
        else:
            class_weights = np.array([1., 1.])

        weights = weights * np.take(class_weights, targets).reshape(weights.shape)

        self.train_on_data(data, weights, targets, self.job_dir)


def _train(commands: SentenceCommands):
    commands.train_model()


def _run_processor(commands: SentenceCommands):
    commands.run_processor()


def evaluate(sentence_model, vocabulary, evaluation_dir, batch_size):
    labels_generator = directory_labels_generator(evaluation_dir)
    data, _, weights, targets = sentence_model.map_input(labels_generator, include_labels=True)
    prediction, _ = sentence_model.model.predict(data, batch_size=batch_size)

    print(print_metrics(prediction, targets, vocabulary, sample_weights=weights))




def create_parser() -> ArgumentParser:
    c = load_config()
    parser = ArgumentParser()
    parser.add_argument("-v", "--verbose", type=int, help="Verbosity", default=0)
    parser.add_argument("additional_args", nargs='*', default=[])
    config_out = ArgumentParser(add_help=False)
    config_out.add_argument("--data-out",
                            help="A file to write the yaml configuration of the sentence "
                                 "detector")
    model_parser = model_opts(c)
    # General optional stuff
    subparsers = parser.add_subparsers(title='mode', metavar='CMD',
                                       description='sentence utilities',
                                       help='Options for which sentence utility to run.')
    # training/detector stuff
    train_parser = subparsers.add_parser('train',
                                         parents=[
                                             config_out,
                                             model_parser,
                                             training_parser()
                                         ])
    train_parser.set_defaults(func=_train)
    pparse = subparsers.add_parser('processor',
                                   parents=[processor_parser(), model_parser])
    pparse.set_defaults(func=_run_processor)
    return parser


def model_opts(c):
    models = ArgumentParser(add_help=False, parents=[vocab_opts(c)])
    models.add_argument('--model', default=c['sentences.model'], choices=['deep', 'ensemble'],
                        help="Which tensorflow sentences model to use.")
    models.add_argument('--hparams', default=c['sentences.hparams_file'])
    models.add_argument('--model-file', default=c.get('sentences.model_file', None))
    return models


def vocab_opts(c):
    vocab_opts = ArgumentParser(add_help=False)
    vocab_opts.add_argument('--vocab-dir', default=c['sentences.vocab_dir'],
                            help="Path to the data directory containing the training data ")
    vocab_opts.add_argument('--word-embeddings',
                            help="Path to the .vec word model")
    vocab_opts.add_argument('--words-list', default=c['sentences.words_list'],
                            help="Path to the txt indexed list of words and vocabulary files")
    return vocab_opts
