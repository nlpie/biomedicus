# Copyright 2019 Regents of the University of Minnesota.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import pytest
from nlpnewt import Events, Pipeline
from nlpnewt._events_service import EventsServicer
from pathlib import Path

import biomedicus
from biomedicus import sentences


@pytest.fixture(name='sentences')
def fixture_sentences():
    pass

def test_sentence_performance():
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'sentences'
    with Events(stub=EventsServicer()) as events, Pipeline() as pipeline:
        for
