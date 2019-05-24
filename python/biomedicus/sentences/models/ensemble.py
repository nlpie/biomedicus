import argparse

import tensorflow as tf

from .deep import BiLSTMSentenceModel, deep_hparams_parser
from biomedicus.sentences.vocabulary import Vocabulary


def ensemble_hparams_parser():
    parser = argparse.ArgumentParser(add_help=False, parents=[deep_hparams_parser()])
    parser.add_argument("--base-weights-file",
                        help="The weights file for the already trained sentence model.")
    return parser


class MultiSentenceModel(BiLSTMSentenceModel):
    """The ensemble sentence model.

    """

    def __init__(self, vocabulary: Vocabulary, args):
        """Creates a new ensemble sentence model.

        Parameters
        ----------
        vocabulary: Vocabulary
            The vocabulary object.
        model_a: BiLSTMSentenceModel
            Already trained sentence model
        kwargs: dict
            All the parameters for BiLSTMSentenceModel
        """
        self.model_a = BiLSTMSentenceModel(vocabulary, args)
        if args.base_weights_file:
            self.model_a.model.load_weights(args.base_weights_file)
        super().__init__(vocabulary, args)

    def _build_model(self):
        inputs, context = self.build_layers()
        self.model_a.model.trainable = False
        _, a_context = self.model_a.model(inputs)

        context_sum = tf.keras.layers.Add()([a_context, context])

        context_sum = tf.keras.layers.BatchNormalization(
            name='corrected_word_representation'
        )(context_sum)

        logits = tf.keras.layers.TimeDistributed(
            tf.keras.layers.Dense(1,
                                  activation='sigmoid',
                                  kernel_regularizer=tf.keras.regularizers.l1()),
            name='logits'
        )(context_sum)

        return tf.keras.models.Model(inputs=inputs, outputs=[logits, context_sum])

    def compile_model(self, optimizer):
        self.model.compile(optimizer=optimizer,
                           sample_weight_mode='temporal',
                           loss={
                               'logits': 'binary_crossentropy',
                               'corrected_word_representation': None
                           },
                           weighted_metrics={
                               'logits': ['binary_accuracy']
                           },
                           loss_weights={
                               'logits': 1.,
                               'corrected_word_representation': 0
                           })
