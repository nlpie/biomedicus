import argparse
import sys

import tensorflow as tf
import yaml

from .base import SentenceDetector, token_text
from .deep import BiLSTMSentenceModel, DeepMain
from .vocabulary import Vocabulary, write_words


class MultiSentenceModel(BiLSTMSentenceModel):
    """The ensemble sentence model.

    """

    def __init__(self, vocabulary: Vocabulary, model_a: BiLSTMSentenceModel, **kwargs):
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
        self.model_a = model_a
        super().__init__(vocabulary, **kwargs)

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


def main():
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
    parser.add_argument("--weights-file-a",
                        help="The weights file for the already trained sentence model.")
    parser.add_argument("--weights-file-b",
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

    deep_main = DeepMain()
    deep_main.add_args(parser)

    args = parser.parse_args()

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

    model_a = BiLSTMSentenceModel(vocabulary, **options)
    model_b = MultiSentenceModel(vocabulary, model_a, **options)

    if args.mode == 'plot_model':
        tf.keras.utils.plot_model(model_b.model, show_shapes=True, to_file="model.png")
        return

    if args.verbose:
        print("\n## HYPERPARAMETERS ##")
        print(model_a.hparams())

    if args.weights_file_a is None:
        print()
        return 1
    model_a.load_weights(args.weights_file_a)

    if args.weights_file_b is not None:
        model_b.load_weights(args.weights_file_b)

    input_dir = args.input

    detector = SentenceDetector(model_b, vocabulary, **options)

    if args.mode == 'train':
        detector.train_model(job_dir=job_dir, training_dir=input_dir)
        if args.config_out is not None:
            model_b.save_config(args.config_out)
    elif args.mode == 'write_config':
        if args.config_out is not None:
            model_b.save_config(args.config_out)
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


if __name__ == "__main__":
    main()
