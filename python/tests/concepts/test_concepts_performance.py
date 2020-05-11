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
from mtap import EventsClient, RemoteProcessor, Pipeline, LocalProcessor
from mtap.io.serialization import PickleSerializer
from mtap.metrics import Accuracy, Metrics
from mtap.utilities import find_free_port

import biomedicus


@pytest.fixture(name='concepts_service')
def fixture_concepts_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = biomedicus.biomedicus_jar()
    p = Popen(['java', '-cp', biomedicus_jar,
               'edu.umn.biomedicus.concepts.DictionaryConceptDetector', '-p', port,
               '--events', events_service], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.performance
def test_concepts_performance(events_service, concepts_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'concepts'
    recall = Accuracy(name='recall', mode='any', fields=['cui'])
    precision = Accuracy(name='precision', mode='any', fields=['cui'])
    with EventsClient(address=events_service) as client, \
            Pipeline(
                RemoteProcessor(processor_id='biomedicus-concepts', address=concepts_service),
                LocalProcessor(Metrics(recall, tested='umls_concepts', target='gold_concepts'),
                               component_id='metrics', client=client),
                LocalProcessor(Metrics(precision, tested='gold_concepts', target='umls_concepts'),
                               component_id='metrics_reverse', client=client)
            ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                pipeline.run(document)

    print('Precision:', precision.value)
    print('Recall:', recall.value)
    timing_info = pipeline.processor_timer_stats()[0].timing_info
    test_results['Concepts'] = {
        'Precision': precision.value,
        'Recall': recall.value,
        'Remote Call Duration': str(timing_info['remote_call'].mean),
        'Process Method Duration': str(timing_info['process_method'].mean)
    }
    assert recall.value > 0.6
