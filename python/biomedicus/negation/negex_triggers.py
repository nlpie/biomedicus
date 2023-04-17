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
from typing import Dict, Any

import mtap
from biomedicus.negation.negex import NegexTagger
from mtap import Document, DocumentProcessor
from mtap.descriptors import labels, parameter, processor, label_property


@processor(
    name='biomedicus-negex-triggers',
    human_name='Negex Triggers Tagger',
    description='Labels phrases which are negation triggers.',
    parameters=[
        parameter(
            name='terms_index',
            data_type='str',
            description='The label index containing terms that should be checked for negation'
        )
    ],
    inputs=[
        labels(
            name='sentences',
            reference='biomedicus-sentences/sentences'
        ),
        labels(
            name='umls_terms',
            reference='biomedicus-concepts/umls_terms',
            name_from_parameter='terms_index'
        )
    ],
    outputs=[
        labels("negation_trigger", description="Spans of phrases that trigger negation.",
               properties=[
                   label_property("tags", data_type='List[str]',
                                  description='The tags that apply to the trigger, '
                                              'for example: POST PREN')
               ])
    ],
    additional_data={
        'entry_point': __name__,
    }
)
class NegexTriggersProcessor(DocumentProcessor):
    def __init__(self):
        self.negex = NegexTagger()

    def process_document(self, document: Document, params: Dict[str, Any]):
        label_trigger = document.get_labeler('negation_triggers')
        with label_trigger:
            for sentence in document.labels['sentences']:
                triggers = self.negex.detect_negex_triggers(sentence.text)
                for start_index, end_index, tags in triggers:
                    label_trigger(sentence.start_index + start_index,
                                  sentence.start_index + end_index,
                                  tags=tags)


def main(args=None):
    mtap.run_processor(NegexTriggersProcessor(), args=args)


if __name__ == '__main__':
    main()
