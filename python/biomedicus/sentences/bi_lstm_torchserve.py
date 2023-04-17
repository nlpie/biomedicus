# Copyright 2020 Regents of the University of Minnesota.
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
from argparse import ArgumentParser
from typing import Dict, Any

import mtap
import requests
from mtap import DocumentProcessor, processor_parser, run_processor
from mtap.descriptors import labels, processor

logger = logging.getLogger("biomedicus.sentences.bi_lstm_torchserve")


@processor('biomedicus-sentences',
           human_name="Sentence Detector",
           description="Labels sentences given document text.",
           entry_point=__name__,
           outputs=[
               labels('sentences')
           ])
class SentencesProcessor(DocumentProcessor):
    def __init__(self, torchserve_address):
        self.torchserve_address = torchserve_address
        logger.info('Using "%s" as endpoint', torchserve_address)

    def process_document(self, document: 'mtap.Document', params: Dict[str, Any]):
        payload = {'text': str(document.text)}
        r = requests.post(self.torchserve_address, data=payload)
        result = r.json()
        with document.get_labeler('sentences', distinct=True) as create_sentence:
            for begin, end in result:
                create_sentence(begin, end)


def main(args=None):
    parser = ArgumentParser(parents=[processor_parser()])
    parser.add_argument(
        '--torchserve-address',
        default='http://localhost:8080/predictions/sentences-bilstm',
        help="The endpoint for the torchserve deployment of the sentences model."
    )

    conf = parser.parse_args(args)
    logging.basicConfig(level=getattr(logging, conf.log_level, logging.INFO))
    run_processor(proc=SentencesProcessor(conf.torchserve_address), namespace=conf)


if __name__ == '__main__':
    main()
