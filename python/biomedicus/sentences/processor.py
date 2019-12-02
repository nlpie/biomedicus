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
import re
from argparse import ArgumentParser
from typing import Dict, Any

import tensorflow as tf
from mtap import processor_parser, run_processor
from mtap.events import Document
from mtap.processing import DocumentProcessor
from mtap.processing.descriptions import label_index, processor

from biomedicus.config import load_config
from biomedicus.sentences.data import InputFn
from biomedicus.sentences.vocabulary import load_char_mapping
from biomedicus.utilities.embeddings import load_words

logger = logging.getLogger(__name__)

_word_pattern = re.compile(r'[\w.\']+')
_punct = re.compile(r'[.:!,;"\']')


def pre_process(text):
    priors = []
    words = []
    posts = []
    tokens = ([(0, 0)] + [(m.start(), m.end()) for m in _word_pattern.finditer(text)]
              + [(len(text), len(text))])
    for i in range(1, len(tokens) - 1):
        _, prev_end = tokens[i - 1]
        start, end = tokens[i]
        next_start, _ = tokens[i + 1]
        priors.append(text[prev_end:start])
        words.append(text[start:end])
        posts.append(text[end:next_start])

    return priors, words, posts, tokens[1:-1]


def predict(model, text, input_fn):
    priors, words, posts, tokens = pre_process(text)
    indices = tf.range(0, limit=len(priors), dtype=tf.int64)
    indices = tf.expand_dims(indices, -1)
    indices = tf.concat([tf.zeros((len(priors), 1), dtype=tf.int64), indices], -1)
    priors = tf.sparse.SparseTensor(indices=indices, values=priors, dense_shape=[1, len(priors)])
    words = tf.sparse.SparseTensor(indices=indices, values=words, dense_shape=[1, len(words)])
    posts = tf.sparse.SparseTensor(indices=indices, values=posts, dense_shape=[1, len(posts)])
    input_data, _ = input_fn(priors, words, posts, None)
    scores = model.predict_on_batch(input_data)
    predictions = tf.math.rint(scores)
    sentences = []
    start_index = None
    prev_end = None
    for (start, end), prediction in zip(tokens, predictions[0]):
        if prediction == 1:
            if start_index is not None:
                end_punct = _punct.match(text, prev_end)
                if end_punct is not None:
                    prev_end = end_punct.end()
                sentences.append((start_index, prev_end))
            start_index = start
        prev_end = end
    if start_index is not None:
        sentences.append((start_index, prev_end))
    return sentences


_split = re.compile(r'(?!\n\n|^_+$|^-+$|^=+$)(.*\w.*)', re.MULTILINE)


@processor('biomedicus-sentences',
           human_name="Sentence Detector",
           description="Labels sentences given document text.",
           entry_point=__name__,
           outputs=[
               label_index('sentences')
           ])
class SentenceProcessor(DocumentProcessor):
    def __init__(self, model, input_fn):
        logger.info("Initializing sentence processor.")
        self.model = model
        self.input_fn = input_fn

    def process_document(self, document: Document, params: Dict[str, Any]):
        with document.get_labeler('sentences', distinct=True) as add_sentence:
            for match in _split.finditer(document.text):
                start = match.start()
                for start_index, end_index in predict(self.model, match.group(0), self.input_fn):
                    add_sentence(start + start_index, start + end_index)


def main(args=None):
    biomedicus_config = load_config()
    logging.basicConfig(level=logging.INFO)
    parser = ArgumentParser(parents=[processor_parser()])
    parser.add_argument('--model-file',
                        default=biomedicus_config['sentences.modelFile'],
                        help="Override path to the serialized Tensorflow model file.")
    parser.add_argument('--words-file',
                        default=biomedicus_config['sentences.wordsFile'],
                        help="Override path to the list of words.")
    parser.add_argument('--chars-file',
                        default=biomedicus_config['sentences.charsFile'],
                        help="Override path to the list of characters.")
    conf = parser.parse_args(args)
    logger.info('Loading words file: %s', conf.words_file)
    words = load_words(conf.words_file)
    logger.info('Loading chars file: %s', conf.chars_file)
    chars_mapping = load_char_mapping(conf.chars_file)
    input_fn = InputFn(chars_mapping, words)
    logger.info('Loading sentences model: %s', conf.model_file)
    model = tf.keras.models.load_model(conf.model_file)
    logger.info('Finished loading sentences model.')
    processor = SentenceProcessor(model, input_fn)
    run_processor(processor, namespace=conf)


if __name__ == '__main__':
    main()
