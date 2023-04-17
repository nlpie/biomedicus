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
from typing import Dict, Any

import stanza
import torch
from mtap import Document, processor, run_processor, processor_parser
from mtap.processing import DocumentProcessor
from mtap.descriptors import labels, label_property

from biomedicus.dependencies.stanza_parser import stanza_deps_and_upos_tags


@processor(
    'biomedicus-selective-dependencies',
    human_name="BioMedICUS Stanza Selective Dependency Parser",
    description="Calls out to the Stanford Stanza framework for dependency parsing"
                "on a appropriate subset of sentences.",
    inputs=[
        labels(name='sentences', reference='biomedicus-sentences/sentences'),
        labels(name='pos_tags', reference='biomedicus-tnt-tagger/pos_tags'),
        labels(
            name='umls_terms',
            reference='biomedicus-concepts/umls_terms',
            name_from_parameter='terms_index'
        ),
        labels(
            "negation_triggers",
            reference='biomedicus-negex-triggers'
        )
    ],
    outputs=[
        labels(
            name='dependencies',
            description="The dependent words.",
            properties=[
                label_property(
                    'deprel',
                    description="The dependency relation",
                    data_type='str'
                ),
                label_property(
                    'head',
                    description="The head of this label or null if its the root.",
                    nullable=True,
                    data_type='ref:dependencies'
                ),
                label_property(
                    'dependents',
                    description="The dependents of ths dependent.",
                    data_type='list[ref:dependencies]'
                )
            ]
        ),
        labels(
            name='upos_tags',
            description="Universal Part-of-speech tags",
            properties=[
                label_property(
                    'tag',
                    description="The Universal Part-of-Speech tag",
                    data_type='str'
                )
            ]
        )
    ],
    additional_data={
        'entry_point': __name__,
    }
)
class StanzaSelectiveParser(DocumentProcessor):
    def __init__(self):
        self.nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse',
                                   tokenize_pretokenized=True, verbose=False)

    def __reduce__(self):
        return StanzaSelectiveParser, ()

    def process_document(self,
                         document: Document,
                         params: Dict[str, Any]):
        pos_tags = document.labels['pos_tags']
        terms_index_name = params.get('terms_index', 'umls_terms')
        terms = document.labels[terms_index_name]
        negation_triggers = document.labels['negation_triggers']

        all_deps = []
        all_upos_tags = []
        sentences = []
        sentence_texts = []
        for sentence in document.labels['sentences']:
            tokens = [(pt.start_index, pt.end_index) for pt in pos_tags.inside(sentence)]
            if len(terms.inside(sentence)) == 0 or len(negation_triggers.inside(sentence)) == 0:
                continue
            sentences.append(tokens)
            sentence_texts.append(sentence.text)

        with torch.no_grad():
            stanza_doc = self.nlp([[document.text[a:b] for a, b in sentence] for sentence in sentences])
        for (sentence, stanza_sentence) in zip(sentences, stanza_doc.sentences):
            sentence_deps, sentence_upos_tags = stanza_deps_and_upos_tags(sentence, stanza_sentence)
            all_deps.extend(sentence_deps)
            all_upos_tags.extend(sentence_upos_tags)

        document.add_labels('dependencies', all_deps)
        document.add_labels('upos_tags', all_upos_tags)


def main(args=None):
    parser = ArgumentParser(parents=[processor_parser()])
    parser.add_argument('--offline', action='store_true')
    parser.add_argument(
        '--mp', action='store_true',
        help="Whether to use the multiprocessing pool based processor server."
    )
    parser.add_argument(
        '--mp-start-method', default='forkserver', choices=['forkserver', 'spawn'],
        help="The multiprocessing start method to use"
    )

    options = parser.parse_args(args)

    if not options.offline:
        stanza.download('en')
    processor = StanzaSelectiveParser()
    mp_context = None
    if options.mp:
        mp_context = torch.multiprocessing.get_context(options.mp_start_method)
    run_processor(processor, options=options, mp=options.mp, mp_context=mp_context)


if __name__ == '__main__':
    main()
