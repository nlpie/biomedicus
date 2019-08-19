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
from pathlib import Path
from subprocess import PIPE, Popen

import pytest
from nlpnewt import EventsClient, Pipeline, RemoteProcessor
from nlpnewt.io.serialization import get_serializer
from nlpnewt.utils import find_free_port


@pytest.fixture(name='normalization_processor')
def fixture_normalization_processor(events_service, processor_watcher):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = os.environ['BIOMEDICUS_JAR']
    p = Popen(['java', '-cp', biomedicus_jar,
               'edu.umn.biomedicus.normalization.NormalizationProcessor',
               '-p', port, '--events', events_service],
              start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    yield from processor_watcher(address, p)


def test_normalization(events_service, normalization_processor):
    json_serializer = get_serializer('json')
    with EventsClient(address=events_service) as client, \
            Pipeline(RemoteProcessor(processor_id='biomedicus_normalizer',
                                     address=normalization_processor)) as pipeline, \
            json_serializer.file_to_event(Path(__file__).parent / '97_95.json',
                                          client=client) as event:
        document = event.documents['plaintext']
        pipeline.run(document)
        for norm_form in document.get_label_index('norm_forms'):
            if norm_form.get_covered_text(document.text) == "according":
                assert norm_form.norm == "accord"
            if norm_form.get_covered_text(document.text) == "expressing":
                assert norm_form.norm == "express"
            if norm_form.get_covered_text(document.text) == "receiving":
                assert norm_form.norm == "receive"
            if norm_form.get_covered_text(document.text) == "days":
                assert norm_form.norm == "day"
