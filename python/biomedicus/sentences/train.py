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
from pathlib import Path, PurePath

import numpy as np
from sklearn.metrics import precision_recall_fscore_support
from tensorflow.keras.callbacks import Callback, EarlyStopping, ModelCheckpoint, TensorBoard
from time import time

from biomedicus.tokenization import detect_space_after, Token


def training_parser():
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
    parser.add_argument('--sequence-length', default=32,
                        help='The sequence size to use during training.')
    parser.add_argument('--sequence-stepping', action='store_true', default=False,
                        help="Whether to step entire sequences, creating non-overlapping "
                             "sequences, instead of the default, which is to step one token at a "
                             "time and create overlapping sequences.")
    parser.add_argument('--job-dir',
                        help="Path to the output directory where logs and models will be "
                             "written.")
    parser.add_argument('--input-dir', help="input directory")
    parser.add_argument('--log-name', help='A name for the tensorboard log file / checkpoints.')
    return parser


def train_on_data(model, config, data, sample_weights, targets, job_dir):
    log_name = build_log_name()

    callbacks = []
    metrics = Metrics(self.vocabulary)
    callbacks.append(metrics)

    if config.tensorboard:
        log_path = PurePath(job_dir) / "logs" / log_name
        tensorboard = TensorBoard(log_dir=log_path)
        callbacks.append(tensorboard)

    if config.checkpoints:
        checkpoint = ModelCheckpoint(PurePath(job_dir) / "models" / log_name + ".h5",
                                     verbose=1,
                                     save_best_only=True)
        callbacks.append(checkpoint)

    model.compile(optimizer=config.optimizer,
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

    if config.early_stopping:
        stopping = EarlyStopping(patience=config.early_stopping_patience,
                                 min_delta=config.early_stopping_delta)
        callbacks.append(stopping)

    model.fit(data,
              {'logits': targets},
              batch_size=config.batch_size,
              epochs=config.epochs,
              sample_weight=sample_weights,
              callbacks=callbacks)


def train_model(model, config):
    class_counts = {}
    docs = []
    starts = []
    ends = []
    labels = []
    for _, txt, tokens in directory_labels_generator(config.input_dir, class_counts=class_counts):
        doc_starts, doc_ends, doc_labels = zip(*[(token.start, token.end, token.label)
                                                 for token in tokens])
        docs.append(txt)
        starts.append(doc_starts)
        ends.append(doc_ends)
        labels.append(doc_labels)

    if config.verbose:
        print("\nClass counts: ")
        print(class_counts)

    if config.use_class_weights:
        print(type(class_counts))
        total = class_counts['B'] + class_counts['I']
        class_weights = np.array([total / (2 * class_counts['I']),
                                  total / (2 * class_counts['B'])])

        if config.verbose:
            print("\nusing class weights: %s" % class_weights)
    else:
        class_weights = np.array([1., 1.])

    weights = weights * np.take(class_weights, targets).reshape(weights.shape)

    train_on_data(model, config, data, weights, targets, self.job_dir)


def directory_labels_generator(directory, repeat=False, class_counts=None):
    import tensorflow as tf
    while True:
        for doc_dir, _, docs in tf.io.gfile.walk(directory):
            for doc in docs:
                if not doc.endswith('.txt'):
                    continue
                path = Path(doc_dir, doc)
                print("reading document {}".format(path))
                with tf.io.gfile.GFile(str(path), 'r') as f:
                    txt = f.read()

                labels_path = path.with_suffix('.labels')
                with tf.io.gfile.GFile(str(labels_path), 'r') as f:
                    tokens = [_split_token_line(txt, x, class_counts) for x in f]
                yield doc, txt, tokens

        if not repeat:
            break


def _split_token_line(txt, line, class_counts=None):
    """Internal method for splitting token lines from the .labels format.
    """
    if not line:
        return None

    split = line.split()

    if len(split) < 5:
        return None

    segment = int(split[0])
    begin = int(split[1])
    end = int(split[2])
    label = split[3]
    if class_counts is not None:
        class_counts[label] += 1
    is_identifier = split[4] == '1'
    space_after = detect_space_after(txt, end)
    return Token(segment, begin, end, label, is_identifier, space_after)


class Metrics(Callback):
    """Keras callback to print out precision, recall, and f-score for each label.

    """

    def __init__(self, vocabulary):
        super(Metrics, self).__init__()
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

        print(print_metrics(scores, labels, vocabulary, weights, logs))


def print_metrics(scores: np.ndarray,
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


def build_log_name(log_name=None):
    return (log_name if log_name is not None else "") + "{}".format(time())
