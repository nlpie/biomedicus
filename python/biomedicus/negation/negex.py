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


"""
from collections import Iterable
from pathlib import Path
from typing import List, Tuple


def make_rules(source: Iterable[str]) -> List[List[str]]:
    rule_list = [line.split('\t')[0].split(' ') for line in source]
    rule_list.sort()
    return rule_list


class NegexTagger:
    def __init__(self, rules: List[List[str]] = None):
        if rules is None:
            with (Path(__file__).parent / 'negex_triggers.txt').open('r') as f:
                rules = make_rules(f)
        self.rules = rules

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
                


        """
        pass


class NegexProcessor:
    pass
