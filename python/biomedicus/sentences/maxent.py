from typing import Dict, Iterable, Tuple, AnyStr, List, Optional

import numpy as np
import tensorflow as tf

from biomedicus.sentences.base import SentenceModel, Main
from biomedicus.sentences.vocabulary import Vocabulary, TokenSequenceGenerator
from biomedicus.tokenization import Token
from biomedicus.utils import default_value


class MaxEntModel(SentenceModel):

    def __init__(self,
                 vocabulary: Vocabulary,
                 svm: Optional[bool] = None,
                 pre_chars: Optional[int] = None,
                 start_chars: Optional[int] = None,
                 end_chars: Optional[int] = None,
                 post_chars: Optional[int] = None,
                 **_):
        del _
        self.vocabulary = vocabulary

        self.svm = default_value(svm, False)

        self.pre_chars = default_value(pre_chars, 7)
        self.start_chars = default_value(start_chars, 7)
        self.end_chars = default_value(end_chars, 7)
        self.post_chars = default_value(post_chars, 7)

        self.n_chars = self.pre_chars + self.start_chars + self.end_chars + self.post_chars

        self._model = self.create_model()

    def create_model(self):
        model = tf.keras.Sequential()
        model.add(tf.keras.layers.Dense(1,
                                        input_shape=(self.n_chars,),
                                        activation='linear' if self.svm else 'sigmoid',
                                        kernel_regularizer=tf.keras.regularizers.l1(),
                                        name='logits'))

        return model

    @property
    def model(self) -> tf.keras.models.Model:
        return self._model

    def compile_model(self, optimizer):
        self.model.compile(optimizer=optimizer,
                           loss='hinge' if self.svm else 'binary_crossentropy',
                           weighted_metrics=['binary_accuracy'])

    def map_input(self,
                  txt_tokens: Iterable[Tuple[AnyStr, List[Token]]],
                  include_labels: bool) -> Tuple:
        generator = MaxEntInputGenerator(txt_tokens,
                                         vocabulary=self.vocabulary,
                                         pre_chars=self.pre_chars,
                                         start_chars=self.start_chars,
                                         end_chars=self.end_chars,
                                         post_chars=self.post_chars,
                                         include_labels=include_labels,
                                         svm=self.svm)
        inputs = next(iter(generator))
        return inputs

    def get_config(self) -> Dict:
        config = dict(self.__dict__)
        config.pop('vocabulary')
        config.pop('_model')
        config.pop('n_chars')
        return config


class MaxEntInputGenerator(TokenSequenceGenerator):

    def __init__(self,
                 input_source: Iterable[Tuple[AnyStr, List[Token]]],
                 vocabulary: Vocabulary,
                 pre_chars: int,
                 start_chars: int,
                 end_chars: int,
                 post_chars: int,
                 include_labels: bool = True,
                 svm: bool = False,
                 batch_size: int = -1):
        super().__init__(input_source, batch_size=batch_size, sequence_length=-1)

        self.vocabulary = vocabulary

        self.pre_chars = pre_chars
        self.start_chars = start_chars
        self.end_chars = end_chars
        self.post_chars = post_chars

        self.batch_count = 0
        self.chars = []
        self.labels = []
        self.weights = []

        self.include_labels = include_labels
        self.svm = svm

        self.class_counts = {'B': 0, 'I': 0, 'O': 0}

    def _handle_token(self):
        self.chars.append(self.get_chars())

        if self.include_labels:
            label_id = self.vocabulary.get_label_id(self.current.label)
            if self.svm:
                label_id = -1 if label_id == 0 else 1
            self.class_counts[self.current.label] += 1
            self.labels.append(label_id)
            if self.current.label == 'O':
                self.weights.append(0.)
            else:
                self.weights.append(1.)
        else:
            self.weights.append(1.)

    def _finish_sequence(self):
        raise NotImplementedError

    def _batch(self):
        inputs = np.array(self.chars)
        self.chars = []
        class_counts = self.class_counts
        self.class_counts = {'B': 0, 'I': 0, 'O': 0}
        weights = np.array(self.weights)
        self.weights = []
        if self.include_labels:
            labels = np.array(self.labels)
            self.labels = []
            labels = labels[:, np.newaxis]

            return inputs, class_counts, weights, labels
        else:
            return inputs, class_counts, weights

    def get_chars(self):
        begin = self.current.begin
        end = self.current.end

        prev_end = max(0, begin - self.pre_chars)

        start_end = min(end, begin + self.start_chars)
        end_start = max(end - self.end_chars, begin)

        next_begin = min(len(self.txt), end + self.post_chars)

        prev = self.txt[prev_end:begin]
        post = self.txt[end:next_begin]
        start = self.txt[begin:start_end]
        end = self.txt[end_start:end]

        return ([0] * (self.pre_chars - len(prev))
                + [self.vocabulary.get_character_id(i) for i in prev + start]
                + [0] * (self.start_chars - len(start) + (self.end_chars - len(end)))
                + [self.vocabulary.get_character_id(i) for i in end + post]
                + [0] * (self.post_chars - len(post)))


class MaxEntMain(Main):
    def add_args(self, parser):
        parser.add_argument('--pre-chars', type=int,
                            help="number of characters to include before the word. default is 7.")
        parser.add_argument('--start-chars', type=int,
                            help="number of characters to include at the start of the word. "
                                 "default is 7.")
        parser.add_argument('--end-chars', type=int,
                            help="number of characters to include at the end of the word. "
                                 "default is 7.")
        parser.add_argument('--post-chars', type=int,
                            help="number of characters to include after the word. "
                                 "default is 7.")
        parser.add_argument('--svm', action='store_true',
                            help="Support Vector Machine instead of Max Ent (logistic regression)")

    def get_model(self, vocabulary, **kwargs) -> MaxEntModel:
        return MaxEntModel(vocabulary=vocabulary, **kwargs)


if __name__ == '__main__':
    MaxEntMain().main()
