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

import stanza
from mtap import Document, processor, run_processor, GenericLabel
from mtap.processing import DocumentProcessor
from mtap.processing.descriptions import label_index, label_property

MAX_ITER = 5000


@processor('biomedicus-dependencies',
           human_name="BioMedICUS Stanza Dependency Parser",
           entry_point=__name__,
           description="Calls out to the Stanford Stanza framework for dependency parsing.",
           inputs=[
               label_index(name='sentences', reference='biomedicus-sentences/sentences')
           ],
           outputs=[
               label_index(name='dependencies',
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
                           ]),
               label_index(name='upos_tags',
                           description="Universal Part-of-speech tags",
                           properties=[
                               label_property(
                                   'tag',
                                   description="The Universal Part-of-Speech tag",
                                   data_type='str'
                               )
                           ])
           ])
class StanzaParser(DocumentProcessor):
    def __init__(self):
        stanza.download('en')
        self.nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse',
                                   tokenize_no_ssplit=True)

    def process_document(self,
                         document: Document,
                         params: Dict[str, Any]):
        sentences = document.labels['sentences']

        sentences_text = []
        for sentence in sentences:
            sentences_text.append(sentence.text)

        stanza_doc = self.nlp(sentences_text)

        all_deps = []
        all_upos_tags = []
        for stanza_sentence, sentence in zip(stanza_doc.sentences, sentences):
            dependencies = {}
            stanza_dependencies = stanza_sentence.dependencies
            stanza_dependencies = list(stanza_dependencies)
            i = 0
            while len(stanza_dependencies) > 0:
                i += 1
                if i > MAX_ITER:
                    raise ValueError(
                        'Maximum Iterations reached while processing dependency graph.')
                head, deprel, dep = stanza_dependencies.pop()
                head_id = int(head.id)
                if head_id == 0:
                    head_dep_label = None
                else:
                    try:
                        head_dep_label = dependencies[head_id]
                    except KeyError:
                        stanza_dependencies.insert(0, (head, deprel, dep))
                        continue

                token_begin = sentence.start_index + dep.parent.start_char - stanza_sentence.tokens[
                    0].start_char
                token_end = sentence.start_index + dep.parent.end_char - stanza_sentence.tokens[
                    0].start_char
                dep_label = GenericLabel(token_begin, token_end, head=head_dep_label, deprel=deprel)
                dep_label.reference_cache['dependents'] = []
                dependencies[int(dep.id)] = dep_label
                if head_dep_label is not None:
                    head_dep_label.dependents.append(dep_label)
                all_deps.append(dep_label)

            for word in stanza_sentence.words:
                token = word.parent
                token_begin = sentence.start_index + token.start_char - stanza_sentence.tokens[
                    0].start_char
                token_end = sentence.start_index + token.end_char - stanza_sentence.tokens[
                    0].start_char
                all_upos_tags.append(GenericLabel(token_begin, token_end, tag=word.upos))

        document.add_labels('dependencies', all_deps)
        document.add_labels('upos_tags', all_upos_tags)


def main(args=None):
    run_processor(StanzaParser(), args=args)


if __name__ == '__main__':
    main()
