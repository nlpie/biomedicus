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
"""An implementation of the NegEx algorithm.

NegEx was originally published by Wendy Chapman et al. in "A Simple Algorithm for Identifying
Negated Findings and Diseases in Discharge Summaries", Journal of Biomedical Informatics, 301–310
(2001). This is a Python implementation of the algorithm using the updated triggers list.

Examples
--------
Using the NegexTagger:

>>> from biomedicus.negation.negex import NegexTagger
>>> tagger = NegexTagger()
>>> sentence = "Pt. denies chest pain."
>>> negations, negation_triggers = tagger.check_sentence(sentence, terms=[(11, 22)])
>>> print([sentence[begin:end] for begin, end in negations])
['chest pain.']
>>> print([sentence[begin:end] for begin, end in negation_triggers])
['denies']


"""
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any, Iterable

import mtap
from mtap import Document, processor
from mtap.descriptors import labels, parameter

from biomedicus.core.dawg import DAWG

_word_pattern = re.compile(r'\S+')
_not_word = re.compile(r'[^\w/\-]+')


def _line_to_rule(line: str):
    components = line.split('\t')
    words = components[0].split(' ')
    tag = components[2][1:5]
    return words, tag


def make_rules(source: Iterable[str]) -> List[Tuple[List[str], str]]:
    rule_list = [_line_to_rule(line) for line in source]
    rule_list.sort()
    return rule_list


class NegexTagger:
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

    def _tokenize(self, sentence):
        # tokenize the sentence using a anti-whitespace pattern.
        return [(match.start(), match.end()) for match in _word_pattern.finditer(sentence)]

    def detect_negex_triggers(self, sentence: str) -> List[Tuple[int, int, List[str]]]:
        tokens = self._tokenize(sentence)

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

    def check_sentence(
            self,
            sentence: str,
            terms: List[Tuple[int, int]]
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Checks the sentence for negated terms.

        Args:
            sentence (str): The sentence.
            terms (~typing.List[~typing.Tuple[int, int]]):
                A list of (start offset, end offset) tuples which indicate the locations of terms
                within the sentence to test for negation.

        Returns:
            negated terms (~typing.List[~typing.Tuple[int, int]]):
                The terms in the input which are negated. Start offset, end offset relative to the
                sentence.
            negation triggers (~typing.List[~typing.Tuple[int, int]]):
                The spans of text which are negation triggers.
        """
        if len(terms) == 0:
            return [], []

        tokens = self._tokenize(sentence)

        term_indices = []
        for (term_start, term_end) in terms:
            term_start_index = -1
            for i, (token_start, token_end) in enumerate(tokens):
                if term_start_index == -1 and token_start >= term_start:
                    term_start_index = i
                if token_end >= term_end:
                    term_indices.append((term_start_index, i))
                    break

        # use a DAWG matcher to locate all
        matcher = self.dawg.matcher()
        triggers = []
        for i, (begin, end) in enumerate(tokens):
            word = _not_word.sub('', sentence[begin:end].lower())
            if len(word) > 0:
                hits = matcher.advance(word)
                for length, tags in hits:
                    first_token_idx = i + 1 - length
                    triggers.append((first_token_idx, i, tags))

        negations = []
        neg_triggers = []

        for (term_start, term_end) in term_indices:
            negated = False
            negation_trigger = None
            for i, (trigger_start, trigger_end, tags) in enumerate(triggers):
                if term_end - trigger_end in range(0, self.tokens_range):
                    if 'PREN' in tags:
                        negated = True
                        negation_trigger = (tokens[trigger_start][0], tokens[trigger_end][1])
                if not negated and trigger_start - term_end in range(0, self.tokens_range) and 'POST' in tags:
                    negated = True
                    negation_trigger = (tokens[trigger_start][0], tokens[trigger_end][1])
            if negated:
                negations.append((tokens[term_start][0], tokens[term_end][1]))
                neg_triggers.append(negation_trigger)

        return negations, neg_triggers


@processor(
    name='biomedicus-negex',
    human_name='Negex Negation Detector',
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
            name='umls_terms',
            reference='biomedicus-concepts/umls_terms',
            name_from_parameter='terms_index'
        )
    ],
    outputs=[
        labels("negated", description="Spans of negated terms."),
        labels("negation_triggers", description="Spans of phrases that trigger negation.")
    ],
    additional_data={
        'entry_point': __name__,
    }
)
class NegexProcessor(mtap.processing.DocumentProcessor):

    def __init__(self):
        self.negex = NegexTagger()

    def process_document(self, document: Document, params: Dict[str, Any]):
        terms_index_name = params.get('terms_index', 'umls_terms')
        label_negated = document.get_labeler('negated')
        label_trigger = document.get_labeler('negation_trigger')
        terms = document.labels[terms_index_name]
        with label_negated, label_trigger:
            for sentence in document.labels['sentences']:
                sentence_terms = [(t.start_index - sentence.start_index,
                                   t.end_index - sentence.start_index)
                                  for t in terms.inside(sentence)]
                negations, triggers = self.negex.check_sentence(sentence.text, sentence_terms)
                for start_index, end_index in negations:
                    label_negated(sentence.start_index + start_index, sentence.start_index + end_index)
                for start_index, end_index in triggers:
                    label_trigger(sentence.start_index + start_index, sentence.start_index + end_index)


def main(args=None):
    proc = NegexProcessor()
    mtap.run_processor(proc, args=args)


if __name__ == '__main__':
    main()
