import os

import numpy as np
import tensorflow as tf
from argparse import ArgumentParser

from biomedicus.sentences.utils import _build_log_name, _Metrics
from biomedicus.sentences.vocabulary import directory_labels_generator
from biomedicus.utils import default_value


def training_parser() -> ArgumentParser:
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--epochs', type=int, default=100,
                        help="number of epochs to run training.")
    parser.add_argument('--tensorboard', action='store_true', default=False,
                        help="whether to use a keras.callbacks.TensorBoard.")
    parser.add_argument('--checkpoints', type=bool, default=True,
                        help="whether to save the best model during training.")
    parser.add_argument('--early-stopping', type=bool, default=True,
                        help="whether to stop when the model stops improving.")
    parser.add_argument('--early-stopping-patience', type=int, default=5,
                        help="how many epochs without improvement before stopping.")
    parser.add_argument('--early-stopping-delta', type=float, default=0.0001,
                        help="the smallest amount loss needs to improve by to be considered "
                             "improvement by early stopping.")
    parser.add_argument('--use-class-weights', type=bool, default=True,
                        help="whether to weight the value of class loss and accuracy based on "
                             "their support.")
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help="the fraction of the data to use for validation.")
    parser.add_argument('--optimizer', default='nadam',
                        help="the keras optimizer to use. default is 'nadam'")
    parser.add_argument('--batch-size', default=32,
                        help="The batch size to use during training.")
    return parser


class SentenceTraining:

    def __init__(self, args):
        self.epochs = args.epochs
        self.tensorboard = args.tensorboard
        self.early_stopping_patience = args.early_stopping_patience
        self.checkpoints = args.checkpoints
        self.validation_split = args.validation_split
        self.early_stopping_delta = args.early_stopping_delta
        self.optimizer = args.optimizer
        self.use_class_weights = args.use_class_weights
        self.early_stopping = args.early_stopping
        self.verbose = args.verbose

        self._sentence_model = None
        self._vocabulary = None

    @property
    def sentence_model(self):
        return self._sentence_model

    @sentence_model.setter
    def sentence_model(self, value):
        self._sentence_model = value

    @property
    def vocabulary(self):
        return self._vocabulary

    @vocabulary.setter
    def vocabulary(self, value):
        self._vocabulary = value

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
        log_name = _build_log_name()

        callbacks = []
        metrics = _Metrics(self.vocabulary)
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

        self.sentence_model.model.fit(data,
                                      {'logits': targets},
                                      batch_size=self.batch_size,
                                      epochs=self.epochs,
                                      sample_weight=sample_weights,
                                      validation_split=self.validation_split,
                                      callbacks=callbacks)

    def train_model(self, job_dir: str, training_dir: str):
        """Trains a sentence detector model using a labeled training set

        Parameters
        ----------
        job_dir: str
            where to store output tensorboard logs and models
        training_dir : str
            directory containing labeled training data

        Returns
        -------
        None
        """
        labels_generator = directory_labels_generator(training_dir)
        data, class_counts, weights, targets = self.sentence_model.map_input(labels_generator,
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

        self.train_on_data(data, weights, targets, job_dir)
