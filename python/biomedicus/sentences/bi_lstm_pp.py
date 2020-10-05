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
import signal
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, Any, Tuple, List

import numpy as np
import torch
import torch.multiprocessing as mp
import yaml
from mtap import Document, DocumentProcessor, processor, run_processor, processor_parser
from mtap.processing.descriptions import labels

from biomedicus.config import load_config
from biomedicus.deployment.deploy_biomedicus import check_data
from biomedicus.sentences.bi_lstm import BiLSTM, predict_text
from biomedicus.sentences.input import InputMapping
from biomedicus.sentences.vocabulary import load_char_mapping, n_chars
from biomedicus.utilities.embeddings import load_vectors

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader as Loader, Dumper as Dumper

logger = logging.getLogger("biomedicus.sentences.bi_lstm_pp")

torch.multiprocessing.set_start_method('spawn', force=True)

"""
Multiprocessing of documents using the pool 
"""

process_locals = {}


def setup_process(model, mapper, log_level):
    def signal_handler(sig, frame):
        pass

    signal.signal(signal.SIGINT, signal_handler)
    if log_level is not None:
        logging.basicConfig(level=getattr(logging, log_level))
    model = torch.jit.script(model)
    model.eval()
    process_locals['model'] = model
    process_locals['mapper'] = mapper


def predict_sentences_async(text) -> List[Tuple[int, int]]:
    result = []
    for start, end in predict_text(process_locals['model'], process_locals['mapper'], text):
        result.append((start, end))
    return result


@processor('biomedicus-sentences',
           human_name="Sentence Detector",
           description="Labels sentences given document text.",
           entry_point=__name__,
           outputs=[
               labels('sentences')
           ])
class SentenceProcessor(DocumentProcessor):
    def __init__(self, model, input_mapping, pool_processes, log_level):
        self.pool = mp.Pool(pool_processes, initializer=setup_process,
                            initargs=(model, input_mapping, log_level))

    def process_document(self, document: Document, params: Dict[str, Any]):
        text = document.text
        result = self.pool.apply(predict_sentences_async, args=(text,))
        with document.get_labeler('sentences', distinct=True) as add_sentence:
            for start, end in result:
                add_sentence(start, end)

    def close(self):
        self.pool.close()
        self.pool.join()


def processor(conf):
    check_data(conf.download_data)
    proc = create_processor(conf)
    run_processor(proc, namespace=conf)


def create_processor(conf):
    config = load_config()
    if conf.embeddings is None:
        conf.embeddings = Path(config['sentences.wordEmbeddings'])
    if conf.chars_file is None:
        conf.chars_file = Path(config['sentences.charsFile'])
    if conf.hparams_file is None:
        conf.hparams_file = Path(config['sentences.hparamsFile'])
    if conf.model_file is None:
        conf.model_file = Path(config['sentences.modelFile'])

    logger.info('Loading hparams from: {}'.format(conf.hparams_file))
    with conf.hparams_file.open('r') as f:
        d = yaml.load(f, Loader)

        class Hparams:
            pass

        hparams = Hparams()
        hparams.__dict__.update(d)
    logger.info('Loading word embeddings from: "{}"'.format(conf.embeddings))
    words, vectors = load_vectors(conf.embeddings)
    vectors = np.array(vectors)
    logger.info('Loading characters from: {}'.format(conf.chars_file))
    char_mapping = load_char_mapping(conf.chars_file)
    input_mapping = InputMapping(char_mapping, words, hparams.word_length)
    model = BiLSTM(hparams, n_chars(char_mapping), vectors)
    logger.info('Loading model weights from: {}'.format(conf.model_file))
    with conf.model_file.open('rb') as f:
        state_dict = torch.load(f)
        model.load_state_dict(state_dict)
    pool_processes = conf.pool_processes
    if pool_processes is None:
        pool_processes = conf.workers
    proc = SentenceProcessor(model, input_mapping, pool_processes, conf.log_level)
    return proc


def main(args=None):
    parser = ArgumentParser(parents=[processor_parser()])
    parser.add_argument('--embeddings', type=Path,
                        default=None,
                        help='Optional override for the embeddings file to use.')
    parser.add_argument('--chars-file', type=Path,
                        default=None,
                        help='Optional override for the chars file to use')
    parser.add_argument('--hparams-file', type=Path,
                        default=None,
                        help='Optional override for model hyperparameters file')
    parser.add_argument('--model-file', type=Path,
                        default=None,
                        help='Optional override for model weights file.')
    parser.add_argument('--download-data', action="store_true",
                        help="Automatically Download the latest model files if they "
                             "are not found.")
    parser.add_argument('--pool-processes', type=int, default=None,
                        help="The number of processes to use for multiprocessing the ")

    conf = parser.parse_args(args)

    if conf.log_level is not None:
        logging.basicConfig(level=getattr(logging, conf.log_level))

    processor(conf)


if __name__ == '__main__':
    main()
