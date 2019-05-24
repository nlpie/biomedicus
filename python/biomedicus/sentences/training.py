import os
from argparse import ArgumentParser
from typing import Optional

import numpy as np
import tensorflow as tf

from biomedicus.sentences.utils import _build_log_name, _Metrics
from biomedicus.sentences.vocabulary import directory_labels_generator
from biomedicus.utils import default_value


def training_parser() -> ArgumentParser:
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--epochs', type=int,
                        help="number of epochs to run training. defaults to 100.")
    parser.add_argument('--tensorboard', action='store_true',
                        help="whether to use a keras.callbacks.TensorBoard. default is False.")
    parser.add_argument('--checkpoints', type=bool,
                        help="whether to save the best model during training. default is True.")
    parser.add_argument('--early-stopping', type=bool,
                        help="whether to stop when the model stops improving. default is True.")
    parser.add_argument('--early-stopping-patience', type=int,
                        help="how many epochs without improvement before stopping. "
                             "default is 5.")
    parser.add_argument('--early-stopping-delta', type=float,
                        help="the smallest amount loss needs to improve by to be considered "
                             "improvement by early stopping. default is 0.001")
    parser.add_argument('--use-class-weights', type=bool,
                        help="whether to weight the value of class loss and accuracy based on "
                             "their support. default is True.")
    parser.add_argument('--validation-split', type=float,
                        help="the fraction of the data to use for validation. default is 0.2.")
    parser.add_argument('--optimizer',
                        help="the keras optimizer to use. default is 'nadam'")
    return parser


class SentenceTraining:

    def __init__(self,
                 epochs: Optional[int] = None,
                 batch_size: Optional[int] = None,
                 optimizer: Optional[str] = None,
                 tensorboard: Optional[bool] = None,
                 checkpoints: Optional[bool] = None,
                 early_stopping: Optional[bool] = None,
                 early_stopping_patience: Optional[int] = None,
                 early_stopping_delta: Optional[float] = None,
                 use_class_weights: Optional[bool] = None,
                 validation_split: Optional[float] = None,
                 verbose: Optional[bool] = None):
        """
        Parameters
        ----------
        epochs : int
            the number of epochs to run. defaults to 100
        batch_size : int
            the size of batches. defaults to 32.
        optimizer : str or Optimizer
            the keras optimizer to use
        tensorboard : bool
            whether to write tensorboard logs. defaults to False
        checkpoints : bool
            whether to save the model after every epoch validation loss improves. defaults to True.
        early_stopping : bool
            whether to stop after no improvement for a certain number of epochs. defaults to True.
        early_stopping_patience : int
            number of epochs without improvement before stopping. defaults to 5.
        early_stopping_delta : float
            what constitutes improvement. defaults to 0.0001
        use_class_weights : bool
            true to weight labels by the class distribution. defaults to True
        validation_split : double
            percentage between 0 and 1 of data to use for validation. defaults to 0.2
        verbose : bool
            whether to print debug information. defaults to False.
        """
        self.epochs = default_value(epochs, 100)
        self.tensorboard = default_value(tensorboard, False)
        self.early_stopping_patience = default_value(early_stopping_patience, 10)
        self.checkpoints = default_value(checkpoints, True)
        self.batch_size = default_value(batch_size, 32)
        self.validation_split = default_value(validation_split, .2)
        self.early_stopping_delta = default_value(early_stopping_delta, .0001)
        self.optimizer = default_value(optimizer, 'nadam')
        self.use_class_weights = default_value(use_class_weights, True)
        self.early_stopping = default_value(early_stopping, True)
        self.verbose = default_value(verbose, True)

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
