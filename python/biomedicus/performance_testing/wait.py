#  Copyright 2020 Regents of the University of Minnesota.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from argparse import ArgumentParser
from time import sleep
from typing import Dict, Any

from mtap import processor, Document, processor_parser, run_processor
from mtap.processing import DocumentProcessor


@processor('biomedicus-wait-python')
class WaitProcessor(DocumentProcessor):
    def __init__(self, wait: int):
        self.wait = wait

    def process_document(self, document: Document, params: Dict[str, Any]):
        sleep(self.wait / 1000)


def main(args=None):
    parser = ArgumentParser(parents=[processor_parser()])
    parser.add_argument('--wait', default=50, type=int)
    conf = parser.parse_args(args)
    run_processor(WaitProcessor(conf.wait), namespace=conf)


if __name__ == '__main__':
    main()
