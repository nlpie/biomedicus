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
from time import time

import numpy as np
import tensorflow as tf
from sklearn.metrics import precision_recall_fscore_support
from typing import Dict, Optional, Tuple

from biomedicus.sentences.vocabulary import Vocabulary


class Metrics(tf.keras.callbacks.Callback):
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


def build_log_name():
    return "{}".format(time())


def token_text(text: str):
    def _inner(token: Tuple[int, int, bool]):
        return ("{} " if token[2] else "{}").format(text[token[0]:token[1]])

    return _inner
