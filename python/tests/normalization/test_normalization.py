# Copyright 2022 Regents of the University of Minnesota.
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
from pathlib import Path
from subprocess import PIPE, Popen

import pytest
from mtap import Pipeline, RemoteProcessor
from mtap.serialization import PickleSerializer
from mtap.utilities import find_free_port

from biomedicus import java_support


@pytest.fixture(name='normalization_processor')
def fixture_normalization_processor(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port

    with java_support.create_call(
            'edu.umn.biomedicus.normalization.NormalizationProcessor',
            '-p', port,
            '--events', events_service
    ) as call:
        p = Popen(call, start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.integration
def test_normalization(events_service, normalization_processor):
    with Pipeline(RemoteProcessor(processor_name='biomedicus_normalizer', address=normalization_processor),
                  events_address=events_service) as pipeline:
        with PickleSerializer.file_to_event(Path(__file__).parent / '97_95.pickle',
                                            client=pipeline.events_client) as event:
            document = event.documents['plaintext']
            pipeline.run(document)
            for norm_form in document.get_label_index('norm_forms'):
                if norm_form.text == "according":
                    assert norm_form.norm == "accord"
                if norm_form.text == "expressing":
                    assert norm_form.norm == "express"
                if norm_form.text == "receiving":
                    assert norm_form.norm == "receive"
                if norm_form.text == "days":
                    assert norm_form.norm == "day"
