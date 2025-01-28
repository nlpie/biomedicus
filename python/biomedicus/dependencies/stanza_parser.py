#  Copyright (c) Regents of the University of Minnesota.
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

import numpy as np
import stanza
import torch
from mtap import Document, DocumentProcessor, processor, run_processor, GenericLabel
from mtap.descriptors import labels, label_property

MAX_ITER = 5000


def stanza_deps_and_upos_tags(sentence, stanza_sentence):
    sentence_deps = []
    sentence_upos_tags = []
    stanza_dependencies = stanza_sentence.dependencies
    stanza_dependencies = list(stanza_dependencies)
    i = 0
    graph = np.zeros((len(stanza_dependencies) + 1, len(stanza_dependencies) + 1))
    dep_map = {}
    for head, deprel, dep in stanza_dependencies:
        graph[int(head.id), int(dep.id)] = 1
        dep_map[int(dep.id)] = (dep, deprel)
    dependencies = {}
    q = [0]
    while len(q) > 0:
        i += 1
        head_id = q.pop()
        head_dep_label = dependencies.get(head_id)
        if head_id != 0 and head_dep_label is None:
            raise ValueError("Dep seen before governor.")
        for dep_id in range(len(stanza_dependencies) + 1):
            if graph[head_id, dep_id] > 0:
                dep, deprel = dep_map[dep_id]
                token_begin, token_end = sentence[dep_id - 1].location
                dep_label = GenericLabel(token_begin, token_end, head=head_dep_label,
                                         deprel=deprel)
                dep_label.reference_cache['dependents'] = []
                dependencies[int(dep.id)] = dep_label
                if head_dep_label is not None:
                    head_dep_label.dependents.append(dep_label)
                q.insert(0, dep_id)
                sentence_deps.append(dep_label)
    if len(dependencies) == len(stanza_dependencies) - 1:
        raise ValueError("Unexpected number of dependencies")
    for word in stanza_sentence.words:
        token_begin, token_end = sentence[word.id - 1].location
        sentence_upos_tags.append(GenericLabel(token_begin, token_end, tag=word.upos))
    return sentence_deps, sentence_upos_tags


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
            name_from_parameter='terms_index',
            optional=True
        ),
        labels(
            "negation_triggers",
            reference='biomedicus-negex-triggers',
            optional=True
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
class StanzaParser(DocumentProcessor):
    def __init__(self, selective=False):
        self.nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse',
                                   tokenize_pretokenized=True, verbose=False)
        self.selective = selective

    def __reduce__(self):
        return StanzaParser, ()

    def process_document(self,
                         document: Document,
                         params: Dict[str, Any]):
        pos_tags = document.labels['pos_tags']

        all_deps = []
        all_upos_tags = []
        selective = self.selective or params.get('selective', False)
        if selective:
            terms_index_name = params.get('terms_index', 'umls_terms')
            negation_triggers = document.labels['negation_triggers']
            terms = document.labels[terms_index_name]

        def include(sentence):
            if selective and (len(terms.inside(sentence)) == 0 or len(negation_triggers.inside(sentence)) == 0):
                return False
            return True

        sentences = [sent for sent in document.labels['sentences'] if include(sent)]

        with torch.no_grad():
            stanza_doc = self.nlp([[tag.text for tag in pos_tags.inside(sent)] for sent in sentences])

        for sentence, stanza_sent in zip(sentences, stanza_doc.sentences):
            sentence_tags = pos_tags.inside(sentence)
            sentence_deps, sentence_upos_tags = stanza_deps_and_upos_tags(sentence_tags, stanza_sent)
            all_deps.extend(sentence_deps)
            all_upos_tags.extend(sentence_upos_tags)

        document.add_labels('dependencies', all_deps)
        document.add_labels('upos_tags', all_upos_tags)


def main(args=None):
    run_processor(StanzaParser(), args=args)


if __name__ == '__main__':
    main()
