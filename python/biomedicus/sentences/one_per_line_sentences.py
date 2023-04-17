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
"""Utilities for labeling input files which are pre-formatted to have one sentence per line.

"""
import re
from typing import List, Dict, Any

import mtap
from mtap import Location, Document, processor
from mtap.descriptors import labels

_pattern = re.compile(r'^[\s]*(.*?)[\s]*$', re.MULTILINE)


def get_sentences(text: str) -> List[Location]:
    for match in _pattern.finditer(text):
        yield match.start(1), match.end(1)


@processor(
    name='biomedicus-sentences-one-per-line',
    human_name='One per Line Sentences',
    description='Labels sentences where each line in the input document is a sentence.',
    outputs=[
        labels(name='sentences')
    ],
    additional_data={
        'entry_point': __name__,
    }
)
class OnePerLineSentencesProcessor(mtap.processing.DocumentProcessor):
    def process_document(self, document: Document, params: Dict[str, Any]):
        with document.get_labeler('sentences') as sentence_labeler:
            for start, end in get_sentences(document.text):
                sentence_labeler(start, end)


def main(args=None):
    proc = OnePerLineSentencesProcessor()
    mtap.run_processor(proc, args=args)


if __name__ == '__main__':
    main()
