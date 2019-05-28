import os

import nlpnewt
from argparse import ArgumentParser, Namespace
from typing import List

from . import vocabulary
from .processor import SentenceProcessor
from .training import training_parser, SentenceTraining
from .utils import _print_metrics
from .vocabulary import Vocabulary, directory_labels_generator
from .. import config


def evaluate(sentence_model, vocabulary, evaluation_dir, batch_size):
    labels_generator = directory_labels_generator(evaluation_dir)
    data, _, weights, targets = sentence_model.map_input(labels_generator, include_labels=True)
    prediction, _ = sentence_model.model.predict(data, batch_size=batch_size)

    print(_print_metrics(prediction, targets, vocabulary, sample_weights=weights))


def create_model(vocab: Vocabulary, args: Namespace, additional_args: List[str]):
    hparams = {}
    if args.hparams is not None:
        import yaml
        try:
            from yaml import CLoader as Loader
        except ImportError:
            from yaml import Loader
        with open(args.hparams, 'rb') as f:
            hparams = yaml.load(f, Loader=Loader)
    if args.model == 'deep':
        from . import deep
        p = deep.deep_hparams_parser()
        Model = deep.BiLSTMSentenceModel
    elif args.model == 'ensemble':
        from . import ensemble
        p = ensemble.ensemble_hparams_parser()
        Model = ensemble.MultiSentenceModel
    else:
        raise ValueError('Unrecognized model: ' + args.model)

    p.set_defaults(**hparams)
    model_args = p.parse_args(additional_args)
    model = Model(vocab, model_args)
    if args.weights_file is not None and os.path.isfile(args.weights_file):
        model.model.load_weights(args.weights_file)


def train(args: Namespace, additional_args: List[str]):
    vocab = create_vocabulary(args)
    model = create_model(vocab, args, additional_args)
    training = SentenceTraining()


def write_words(args: Namespace, *_):
    vocabulary.write_words(args.word_embeddings, args.words_list)


def create_vocabulary(args: Namespace):
    return Vocabulary(args.vocab_dir, args.word_embeddings, args.words_list)


def run_processor(args: Namespace, additional_args: List[str]):
    vocab = create_vocabulary(args)
    model = create_model(vocab, args, additional_args)
    processor = SentenceProcessor(model)
    nlpnewt.run_processor(processor, args)


def main(args=None):
    c = config.load_config()

    parser = ArgumentParser()

    general = ArgumentParser(add_help=False)
    general.add_argument("-v", "--verbose", type=int, help="Verbosity", default=0)

    config_out = ArgumentParser(add_help=False)
    config_out.add_argument("--config-out",
                            help="A file to write the yaml configuration of the sentence detector")

    vocab_opts = ArgumentParser(add_help=False)
    vocab_opts.add_argument('--vocab-dir', default=c['sentences.vocab_dir'],
                            help="Path to the data directory containing the training data ")
    vocab_opts.add_argument('--word-embeddings',
                            help="Path to the .vec word model")
    vocab_opts.add_argument('--words-list', default=c['sentences.words_list'],
                            help="Path to the txt indexed list of words and vocabulary files")

    models = ArgumentParser(add_help=False, parents=[vocab_opts])
    models.add_argument('--model', default=c['sentences.model'], choices=['deep', 'ensemble'],
                        help="Which tensorflow sentences model to use.")
    models.add_argument('--hparams', default=c['sentences.hparams_file'])
    models.add_argument('--weights-file', default=c['sentences.weights_file'])

    # General optional stuff

    subparsers = parser.add_subparsers('mode')
    # training/detector stuff
    train_parser = subparsers.add_parser('train',
                                         parents=[
                                             config_out,
                                             models,
                                             training_parser()
                                         ])
    train_parser.add_argument('--job-dir',
                              help="Path to the output directory where logs and models will be "
                                   "written.")
    train_parser.add_argument('--input-dir', help="input directory")
    train_parser.set_defaults(func=train)

    processor_parser = subparsers.add_parser('processor',
                                             parents=[nlpnewt.processor_parser(), models])
    processor_parser.set_defaults(func=run_processor)

    args, additional_args = parser.parse_known_args(args)

    args.func(additional_args)


main()
