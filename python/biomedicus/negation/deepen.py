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
import logging
from typing import Sequence, Dict, Any
from argparse import ArgumentParser

from mtap import GenericLabel, Location, processor, DocumentProcessor, Document, run_processor, processor_parser
from mtap.descriptors import parameter, labels
from mtap.types import LabelIndex

logger = logging.getLogger(__name__)


def check_cc_and(dep: GenericLabel, upos_tags: LabelIndex[GenericLabel]):
    if dep.deprel == 'conj' and upos_tags.at(dep)[0].tag == 'VERB':
        for child in dep.dependents:
            if child.deprel == 'cc' and child.text.lower() == 'and':
                return True
    return False


def check_nmod(child: GenericLabel, negation_location, upos_tags: LabelIndex[GenericLabel]):
    if child.deprel == 'nmod':
        if first_level(child, negation_location, upos_tags):
            return True
    return False


def check_suggest(child: GenericLabel, negation_location: Location, upos_tags):
    if child.deprel == 'acl' and child.text.lower() in ('suggest', 'indicate'):
        if first_level(child, negation_location, upos_tags):
            return True
    return False


def check_conj_or(dep: GenericLabel, negation_location: Location, upos_tags):
    if dep.deprel == 'conj':
        gov = dep.head
        conjs = [child for child in gov.dependents if child.deprel == 'conj']
        conjs.sort(key=lambda x: x.location)
        loc = conjs.index(dep)
        has_or = False
        for child in conjs[-1].dependents:
            if child.deprel == 'cc' and child.text.lower() == 'or':
                has_or = True
        if has_or and loc >= len(conjs) - 4:
            for child in conjs[loc:]:
                if negation_location.covers(child):
                    return True
        return False


def first_level(gov: GenericLabel, negation_location: Location,
                upos_tags: LabelIndex[GenericLabel]):
    if negation_location.covers(gov):
        return True
    if check_conj_or(gov, negation_location, upos_tags):
        return True
    for child in gov.dependents:
        if negation_location.covers(child):
            return True
        if check_suggest(child, negation_location, upos_tags):
            return True
        if check_nmod(child, negation_location, upos_tags):
            return True
        if check_cc_and(child, upos_tags):
            continue
        for second_child in child.dependents:
            if check_cc_and(second_child, upos_tags):
                continue
            if negation_location.covers(second_child):
                return True
            if check_nmod(child, negation_location, upos_tags):
                return True
            if check_suggest(second_child, negation_location, upos_tags):
                return True
    return False


class DeepenTagger:
    def check_sentence(self,
                       terms: Sequence[GenericLabel],
                       triggers: LabelIndex[GenericLabel],
                       deps: LabelIndex[GenericLabel],
                       upos_tags: LabelIndex[GenericLabel]):
        affirmed_negations = []
        affirmed_triggers = []
        for term in terms:
            for trigger in triggers:
                if trigger.start_index <= term.start_index < trigger.end_index:
                    # Trigger overlaps term on the left
                    continue
                if trigger.start_index < term.end_index <= trigger.end_index:
                    # Trigger overlaps term on the right
                    continue
                if term.location.covers(trigger):
                    continue
                if trigger.start_index < term.start_index and 'PREN' not in trigger.tags:
                    continue
                if trigger.start_index > term.end_index and 'POST' not in trigger.tags:
                    continue
                negation_location = term.location
                trigger_location = trigger.location
                trigger_deps = deps.inside(trigger_location)
                if len(trigger_deps) == 0:
                    logger.warning("Negation trigger without deps, should not happen.")
                    continue
                trigger_edge = None
                for dep in trigger_deps:
                    if dep.head not in trigger_deps:
                        trigger_edge = dep
                        break
                gov = trigger_edge
                if gov is None:
                    raise ValueError('Dependency not found.')
                while True:
                    if gov.head is None:
                        break
                    tag = upos_tags.at(gov)[0].tag
                    if tag == 'VERB' or tag == 'NOUN':
                        break
                    if gov.deprel == 'conj':
                        break
                    gov = gov.head

                affirmed = first_level(gov, negation_location, upos_tags)

                if affirmed:
                    affirmed_negations.append(negation_location)
                    affirmed_triggers.append(trigger_location)
                    break

        return affirmed_negations, affirmed_triggers


@processor(
    name='biomedicus-deepen',
    human_name='DEEPEN Negation Detector',
    description='Detects which UMLS terms are negated.',
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
            name='dependencies',
            reference='biomedicus-selective-dependencies/dependencies'
        ),
        labels(
            name='umls_terms',
            reference='biomedicus-concepts/umls_terms',
            name_from_parameter='terms_index'
        )
    ],
    outputs=[
        labels("negated", description="Spans of negated terms."),
        labels("negation_trigger", description="Spans of phrases that trigger negation.")
    ],
    additional_data={
        'entry_point': __name__,
    }
)
class DeepenProcessor(DocumentProcessor):
    def __init__(self):
        self.negex = DeepenTagger()

    def process_document(self, document: Document, params: Dict[str, Any]):
        terms_index_name = params.get('terms_index', 'umls_terms')
        label_negated = document.get_labeler('negated')
        terms = document.labels[terms_index_name]
        triggers = document.labels['negation_triggers']
        deps = document.labels['dependencies']
        upos_tags = document.labels['upos_tags']
        with label_negated:
            for sentence in document.labels['sentences']:
                sentence_terms = terms.inside(sentence)
                sentence_triggers = triggers.inside(sentence)
                if len(sentence_triggers) > 0:
                    negations, _ = self.negex.check_sentence(sentence_terms,
                                                             sentence_triggers,
                                                             deps, upos_tags)
                    for start_index, end_index in negations:
                        label_negated(start_index, end_index)


def main(args=None):
    parser = ArgumentParser(add_help=True, parents=[processor_parser()])
    parser.add_argument(
        '--mp', action='store_true',
        help="Whether to use the multiprocessing pool based processor server."
    )
    parser.add_argument(
        '--mp-start-method', default='forkserver', choices=['forkserver', 'spawn'],
        help="The multiprocessing start method to use"
    )
    options = parser.parse_args(args)
    mp_context = None
    if options.mp:
        import multiprocessing as mp
        mp_context = mp.get_context(options.mp_start_method)

    run_processor(DeepenProcessor(), options=options, mp=options.mp, mp_context=mp_context)


if __name__ == '__main__':
    main()
