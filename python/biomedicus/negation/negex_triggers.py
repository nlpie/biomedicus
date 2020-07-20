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
import re
from pathlib import Path
from typing import Dict, Any, List

import mtap
from mtap import Document
from mtap.processing import DocumentProcessor
from mtap.processing.descriptions import label_index, parameter, processor, label_property

from biomedicus.core.dawg import DAWG
from biomedicus.negation.negex import make_rules

_word_pattern = re.compile(r'\S+')
_not_word = re.compile(r'[^\w/\-]+')


class NegexTriggerTagger:
    def __init__(self, rules: List[List[str]] = None, tokens_range: int = 40):
        if rules is None:
            with (Path(__file__).parent / 'negex_triggers.txt').open('r') as f:
                rules = make_rules(f)
        self.dawg = DAWG()
        for rule, tag in rules:
            try:
                tags = self.dawg[rule]
            except KeyError:
                tags = []
                self.dawg[rule] = tags
            tags.append(tag)
        self.tokens_range = tokens_range

    def detect_negex_triggers(self, sentence: str):
        # tokenize the sentence using a anti-whitespace pattern.
        tokens = []
        for match in _word_pattern.finditer(sentence):
            tokens.append((match.start(), match.end()))

        # use a DAWG matcher to locate all
        matcher = self.dawg.matcher()
        triggers = []
        for i, (begin, end) in enumerate(tokens):
            word = _not_word.sub('', sentence[begin:end].lower())
            if len(word) > 0:
                hits = matcher.advance(word)
                for length, tags in hits:
                    first_token_idx = i + 1 - length
                    triggers.append((tokens[first_token_idx][0], tokens[i][1], tags))
        return triggers


@processor(
    name='biomedicus-negex-triggers',
    human_name='Negex Triggers Tagger',
    description='Labels phrases which are negation triggers.',
    entry_point=__name__,
    parameters=[
        parameter(
            name='terms_index',
            data_type='str',
            description='The label index containing terms that should be checked for negation'
        )
    ],
    inputs=[
        label_index(
            name='sentences',
            reference='biomedicus-sentences/sentences'
        ),
        label_index(
            name='umls_terms',
            reference='biomedicus-concepts/umls_terms',
            name_from_parameter='terms_index'
        )
    ],
    outputs=[
        label_index("negation_trigger", description="Spans of phrases that trigger negation.",
                    properties=[
                        label_property("tags", data_type='List[str]',
                                       description='The tags that apply to the trigger, '
                                                   'for example: POST PREN')
                    ])
    ]
)
class NegexTriggersProcessor(DocumentProcessor):
    def __init__(self):
        self.negex = NegexTriggerTagger()

    def process_document(self, document: Document, params: Dict[str, Any]):
        label_trigger = document.get_labeler('negation_triggers')
        with label_trigger:
            for sentence in document.get_label_index('sentences'):
                triggers = self.negex.detect_negex_triggers(sentence.text)
                for start_index, end_index, tags in triggers:
                    label_trigger(sentence.start_index + start_index,
                                  sentence.start_index + end_index,
                                  tags=tags)


def main(args=None):
    proc = NegexTriggersProcessor()
    mtap.run_processor(proc, args=args)


if __name__ == '__main__':
    main()
