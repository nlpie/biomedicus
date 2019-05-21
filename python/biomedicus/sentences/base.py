import argparse
import os
import sys
from abc import ABCMeta, abstractmethod
from time import time
from typing import Tuple, AnyStr, Dict, List, Optional, Iterable

import numpy as np
import tensorflow as tf
import yaml
from sklearn.metrics import precision_recall_fscore_support

from .vocabulary import directory_labels_generator, Vocabulary, write_words
from ..tokenization import Token, tokenize
from ..utils import default_value


class Main(metaclass=ABCMeta):
    """Class for the utility main methods for the different models

    """

    def __init__(self):
        parser = argparse.ArgumentParser()

        # General optional stuff
        parser.add_argument('mode', choices=['train', 'predict', 'write_config', 'evaluate',
                                             'write_words', 'plot_model'])
        parser.add_argument('-j', '--job-dir',
                            help="Path to the output directory where logs and models will be "
                                 "written.")
        parser.add_argument('-d', '--vocab-dir',
                            help="Path to the data directory containing the training data "
                                 "and vocabulary files")
        parser.add_argument('-i', '--input', help="input directory")
        parser.add_argument('-e', '--word-embeddings',
                            help="Path to the .vec word model")
        parser.add_argument('-w', '--words-list',
                            help="Path to the txt indexed list of words")
        parser.add_argument("--config-file",
                            help="Yaml configuration file. Arguments specified at run take "
                                 "precedence over anything in this file.")
        parser.add_argument("--config-out",
                            help="A file to write the yaml configuration of the sentence detector")
        parser.add_argument("--weights-file",
                            help="The hdf5 file to load model weights from.")
        parser.add_argument("-v", "--verbose", type=int,
                            help="Verbosity", default=0)

        # training/detector stuff
        parser.add_argument('--epochs', type=int,
                            help="number of epochs to run training. defaults to 100.")
        parser.add_argument('--batch-size', type=int,
                            help="number of sequences per minibatch. defaults to 32.")
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

        self.add_args(parser)

        self._parser = parser

    @abstractmethod
    def add_args(self, parser):
        pass

    @abstractmethod
    def get_model(self, vocabulary, **kwargs) -> 'SentenceModel':
        pass

    def main(self):
        args = self._parser.parse_args()

        if args.mode == 'write_words':
            write_words(args.word_embeddings, args.words_list)
            return

        vocab_dir = args.vocab_dir
        word_model = args.word_embeddings
        vocabulary = Vocabulary(vocab_dir, word_model)

        options = {}
        if args.config_file is not None:
            with open(args.config_file, 'r') as config_file:
                options.update(yaml.load(config_file))

        options.update(args.__dict__)

        job_dir = args.job_dir

        model = self.get_model(vocabulary=vocabulary, **options)

        if args.mode == 'plot_model':
            tf.keras.utils.plot_model(model.model, show_shapes=True)
            return

        if args.verbose:
            print("\n## HYPERPARAMETERS ##")
            print(model.hparams())

        detector = SentenceDetector(sentence_model=model, vocabulary=vocabulary, **options)

        if args.weights_file is not None:
            model.load_weights(args.weights_file)

        input_dir = args.input

        if args.mode == 'train':
            detector.train_model(job_dir=job_dir, training_dir=input_dir)
            if args.config_out is not None:
                model.save_config(args.config_out)
        elif args.mode == 'write_config':
            if args.config_out is not None:
                model.save_config(args.config_out)
        elif args.mode == 'predict':
            txt = sys.stdin.read()
            sentences = detector.predict_txt(txt)
            get_text = token_text(txt)
            for sentence in sentences:
                line = "[{} ]:".format(sentence['category'])

                line += "".join(map(get_text, sentence['tokens']))

                print(line)
        elif args.mode == 'evaluate':
            detector.evaluate(evaluation_dir=input_dir)


class SentenceModel(object, metaclass=ABCMeta):
    """Base class for a sentence model

    """

    @property
    @abstractmethod
    def model(self) -> tf.keras.models.Model:
        pass

    @abstractmethod
    def compile_model(self, optimizer):
        pass

    @abstractmethod
    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        pass

    def hparams(self) -> str:
        return "\n".join(["{}: {}".format(k, v) for k, v in self.get_config().items()])

    @abstractmethod
    def get_config(self) -> Dict:
        pass

    def save_config(self, file_path):
        with open(file_path, 'w') as out:
            yaml.dump(self.get_config(), out, default_flow_style=False)

    def save_weights(self, file_path: AnyStr, overwrite: bool = True):
        self.model.save_weights(file_path, overwrite=overwrite)

    def load_weights(self, file_path: AnyStr):
        self.model.load_weights(file_path)


class SentenceDetector(object):
    """Detects sentences in text using a SentenceModel.

    """

    def __init__(self,
                 sentence_model: SentenceModel,
                 vocabulary: Vocabulary,
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
                 verbose: Optional[bool] = None,
                 **_):
        """

        Parameters
        ----------
        sentence_model : SentenceModel
            the model to use to detect sentences
        vocabulary : Vocabulary
            the vocabulary of characters, words, and labels
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
        _ : dict
            unused kwargs.
        """
        del _
        self.sm = sentence_model
        self.epochs = default_value(epochs, 100)
        self.tensorboard = default_value(tensorboard, False)
        self.verbose = default_value(verbose, True)
        self.early_stopping_patience = default_value(early_stopping_patience, 10)
        self.checkpoints = default_value(checkpoints, True)
        self.batch_size = default_value(batch_size, 32)
        self.validation_split = default_value(validation_split, .2)
        self.early_stopping_delta = default_value(early_stopping_delta, .0001)
        self.optimizer = default_value(optimizer, 'nadam')
        self.use_class_weights = default_value(use_class_weights, True)
        self.vocabulary = vocabulary
        self.early_stopping = default_value(early_stopping, True)

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

        self.sm.compile_model(optimizer=self.optimizer)

        if self.early_stopping:
            stopping = tf.keras.callbacks.EarlyStopping(patience=self.early_stopping_patience,
                                                        min_delta=self.early_stopping_delta)
            callbacks.append(stopping)

        self.sm.model.fit(data,
                          {'logits': targets},
                          batch_size=self.batch_size,
                          epochs=self.epochs,
                          sample_weight=sample_weights,
                          validation_split=self.validation_split,
                          callbacks=callbacks)

    def train_model(self, job_dir: AnyStr, training_dir: AnyStr):
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
        data, class_counts, weights, targets = self.sm.map_input(labels_generator,
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

    def evaluate(self, evaluation_dir):
        """Evaluates the model against a set of labeled data.

        Parameters
        ----------
        evaluation_dir : str
            directory containing evaluation labels

        Returns
        -------
        None
        """
        labels_generator = directory_labels_generator(evaluation_dir)
        data, _, weights, targets = self.sm.map_input(labels_generator, include_labels=True)
        prediction, _ = self.sm.model.predict(data, batch_size=self.batch_size)

        print(_print_metrics(prediction, targets, self.vocabulary, sample_weights=weights))

    def predict_txt(self,
                    txt: AnyStr,
                    tokens: Optional[List[Token]] = None,
                    include_tokens: bool = True) -> List[Dict]:
        """Takes input text, tokenizes it, and then returns a list of tokens with labels

        Attributes
        ----------
        txt : str
            the text to predict sentences
        tokens : iterable of Token
            tokens if the text has already been tokenized
        include_tokens : bool
            whether the result sentences should include their tokens

        Returns
        -------
        list
            a list of lists of tokens with their sentence classifications. Each list is a sentence.
        """
        if tokens is None:
            tokens = list(tokenize(txt))

        if len(tokens) == 0:
            return []

        inputs, _, weights = self.sm.map_input([(txt, tokens)], include_labels=False)

        outputs, _ = self.sm.model.predict(inputs, batch_size=self.batch_size)
        outputs = np.rint(outputs)
        not_padding = np.nonzero(weights)
        outputs = ['B' if x == 1 else 'I' for x in outputs[not_padding]]

        # construct results list
        results = []
        prev = None
        sentence = None
        for token, label in zip(tokens, outputs):
            result_token = (token.begin, token.end, token.has_space_after)
            if (label == 'B') or (label == 'O' and (prev is None or prev[1] != 'O')):
                if sentence is not None:
                    sentence['end'] = prev[0].end  # prev token end
                    results.append(sentence)

                sentence = {
                    'begin': token.begin,
                    'category': 'S' if label != 'B' else 'U'
                }
                if include_tokens:
                    sentence['tokens'] = []

            if include_tokens:
                sentence['tokens'].append(result_token)

            prev = token, label

        sentence['end'] = prev[0][2]  # prev token end
        results.append(sentence)
        return results


class _Metrics(tf.keras.callbacks.Callback):
    """Keras callback to print out precision, recall, and f-score for each label.

    """

    def __init__(self, vocabulary):
        super(_Metrics, self).__init__()
        self.vocabulary = vocabulary

    def on_epoch_end(self, _, logs=None):
        del _
        logs = logs or {}

        if len(self.validation_data) == 5:
            inputs = [self.validation_data[0], self.validation_data[1]]
            labels = self.validation_data[2]
            weights = self.validation_data[3]
        else:
            inputs = self.validation_data[0]
            labels = self.validation_data[1]
            weights = self.validation_data[2]

        outputs = self.model.predict(inputs)
        if len(outputs) == 2:
            scores, _ = outputs
        else:
            scores = outputs
        vocabulary = self.vocabulary

        print(_print_metrics(scores, labels, vocabulary, weights, logs))


def _print_metrics(scores: np.ndarray,
                   labels: np.ndarray,
                   vocabulary: Vocabulary,
                   sample_weights: np.ndarray,
                   logs: Optional[Dict] = None):
    y_predict = np.rint(scores.ravel())
    y_true = labels.ravel()
    sample_weights = sample_weights.ravel()

    p, r, f1, s = precision_recall_fscore_support(
        y_true,
        y_predict,
        sample_weight=sample_weights
    )
    by_label = zip(p, r, f1)
    results = "label, precision, recall, f1\n"
    for i, metrics in enumerate(by_label):
        label = vocabulary.get_label(i) if i < vocabulary.labels else 'average'
        if label is None:
            label = 'average'
        if logs is not None:
            logs[label + "/precision"] = metrics[0]
            logs[label + "/recall"] = metrics[1]
            logs[label + "/f1"] = metrics[2]
        results += "{},{},{},{}\n".format(label, metrics[0], metrics[1], metrics[2])
    return results


def _build_log_name():
    return "{}".format(time())


def token_text(text: AnyStr):
    def _inner(token: Tuple[int, int, bool]):
        return ("{} " if token[2] else "{}").format(text[token[0]:token[1]])

    return _inner
