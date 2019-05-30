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

import nlpnewt
from argparse import ArgumentParser, Namespace
from typing import List

from biomedicus import config
from biomedicus.sentences import vocabulary
from biomedicus.sentences.models import SavedModel, deep_hparams_parser, BiLSTMSentenceModel, \
    DeepMapper, MultiSentenceModel, ensemble_hparams_parser
from biomedicus.sentences.processor import SentenceProcessor
from biomedicus.sentences.training import training_parser, SentenceTraining
from biomedicus.sentences.utils import print_metrics
from biomedicus.sentences.vocabulary import Vocabulary, directory_labels_generator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate(sentence_model, vocabulary, evaluation_dir, batch_size):
    labels_generator = directory_labels_generator(evaluation_dir)
    data, _, weights, targets = sentence_model.map_input(labels_generator, include_labels=True)
    prediction, _ = sentence_model.model.predict(data, batch_size=batch_size)

    print(print_metrics(prediction, targets, vocabulary, sample_weights=weights))


def create_model(vocab: Vocabulary, args: Namespace, additional_args: List[str]):
    logger.info('Creating sentences model.')
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
        logger.info('Using deep model.')
        p = deep_hparams_parser()
        Model = BiLSTMSentenceModel
        Mapper = DeepMapper
    elif args.model == 'ensemble':
        logger.info('Using ensemble model.')
        p = ensemble_hparams_parser()
        Model = MultiSentenceModel
        Mapper = DeepMapper
    else:
        raise ValueError('Unrecognized model: ' + args.model)

    p.set_defaults(**hparams)
    model_args = p.parse_args(additional_args)

    if args.model_file is not None and os.path.isfile(args.model_file):
        model = SavedModel(args.model_file)
    else:
        model = Model(vocab, model_args)

    mapper = Mapper(vocab, model_args)

    return model, mapper


def train(args: Namespace, additional_args: List[str]):
    vocab = create_vocabulary(args)
    model, mapper = create_model(vocab, args, additional_args)
    training = SentenceTraining(args)
    training.sentence_model = model
    training.vocabulary = vocab
    training.train_model(args.job_dir, args.input_dir)


def write_words(args: Namespace, *_):
    vocabulary.write_words(args.word_embeddings, args.words_list)


def create_vocabulary(args: Namespace):
    return Vocabulary(args.vocab_dir, args.word_embeddings, args.words_list)


def run_processor(args: Namespace, additional_args: List[str]):
    vocab = create_vocabulary(args)
    model, mapper = create_model(vocab, args, additional_args)
    processor = SentenceProcessor(model, mapper)
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
    models.add_argument('--model-file', default=c.get('sentences.model_file', None))

    # General optional stuff

    subparsers = parser.add_subparsers(title='mode', description='sentence utilities',
                                       help='Options for which sentence utility to run.')
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

    args.func(args, additional_args)


main()
