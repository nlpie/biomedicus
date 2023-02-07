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
from subprocess import Popen, PIPE

import pytest
from mtap import RemoteProcessor, Pipeline, LocalProcessor
from mtap.metrics import Accuracy, Metrics
from mtap.serialization import PickleSerializer
from mtap.utilities import find_free_port

from biomedicus.java_support import create_call


@pytest.fixture(name='concepts_service')
def fixture_concepts_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    with create_call(
            'edu.umn.biomedicus.concepts.DictionaryConceptDetector',
            '-p', port,
            '--events', events_service
    ) as call:
        p = Popen(call, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.performance
def test_concepts_performance(events_service, concepts_service, test_results):
    try:
        input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'concepts'
    except KeyError:
        pytest.fail("Missing required environment variable BIOMEDICUS_TEST_DATA")
    recall = Accuracy(name='recall', mode='any', fields=['cui'])
    precision = Accuracy(name='precision', mode='any', fields=['cui'])
    with Pipeline(
            RemoteProcessor(processor_name='biomedicus-concepts', address=concepts_service),
            LocalProcessor(Metrics(recall, tested='umls_concepts', target='gold_concepts'),
                           component_id='metrics'),
            LocalProcessor(Metrics(precision, tested='gold_concepts', target='umls_concepts'),
                           component_id='metrics_reverse'),
            events_address=events_service
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=pipeline.events_client) as event:
                document = event.documents['plaintext']
                pipeline.run(document)

    print('Precision:', precision.value)
    print('Recall:', recall.value)
    timing_info = pipeline.processor_timer_stats('biomedicus-concepts').timing_info
    test_results['Concepts'] = {
        'Precision': precision.value,
        'Recall': recall.value,
        'Remote Call Duration': str(timing_info['remote_call'].mean),
        'Process Method Duration': str(timing_info['process_method'].mean)
    }
    assert recall.value > 0.6
