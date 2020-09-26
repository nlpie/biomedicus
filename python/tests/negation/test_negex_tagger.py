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
from biomedicus.negation.negex import NegexTagger


def test_without_abbrev():
    negex_tagger = NegexTagger()
    terms, triggers = negex_tagger.check_sentence('Given that the pt was w/o evidence of DVT', [(38, 41)])
    assert (38, 41) in terms
    assert (22, 25) in triggers
