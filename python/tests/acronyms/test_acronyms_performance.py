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
from mtap import EventsClient, Pipeline, RemoteProcessor, LocalProcessor
from mtap.io.serialization import JsonSerializer
from mtap.metrics import Accuracy, Metrics
from mtap.utilities import find_free_port

import biomedicus


@pytest.fixture(name='acronyms_service')
def fixture_acronyms_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = biomedicus.biomedicus_jar()
    p = Popen(['java', '-cp', biomedicus_jar, 'edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
               '-p', port, '--events', events_service],
              start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.phi_performance
def test_acronyms_performance(events_service, acronyms_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_PHI_TEST_DATA']) / 'acronyms'
    top_score_accuracy = Accuracy(name='top_score_accuracy', fields=['expansion'])
    any_accuracy = Accuracy(name='any_accuracy', mode='any', fields=['expansion'])
    detection_recall = Accuracy(name='detection_recall', mode='location', fields=['expansion'])
    detection_precision = Accuracy(name='detection_precision', mode='location',
                                   fields=['expansion'])
    with EventsClient(address=events_service) as client, Pipeline(
        RemoteProcessor(processor_id='biomedicus-acronyms', address=acronyms_service),
        LocalProcessor(Metrics(top_score_accuracy, detection_recall, tested='acronyms',
                               target='gold_acronyms'),
                       component_id='top_score_metrics', client=client),
        LocalProcessor(Metrics(detection_precision, tested='gold_acronyms', target='acronyms'),
                       component_id='top_score_reverse', client=client),
        LocalProcessor(Metrics(any_accuracy, tested='all_acronym_senses', target='gold_acronyms'),
                       component_id='all_senses_metrics', client=client)
    ) as pipeline:
        for test_file in input_dir.glob('**/*.json'):
            with JsonSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                pipeline.run(document)

        print('Top Sense Accuracy:', top_score_accuracy.value)
        print('Any Sense Accuracy:', any_accuracy.value)
        print('Detection Recall:', detection_recall.value)
        print('Detection Precision:', detection_precision.value)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats('biomedicus-acronyms').timing_info
        test_results['acronyms'] = {
            'Top sense accuracy': top_score_accuracy.value,
            'Any sense accuracy': any_accuracy.value,
            'Detection Recall': detection_recall.value,
            'Detection Precision': detection_precision.value,
            'Remote Call Duration': str(timing_info['remote_call'].mean),
            'Process Method Duration': str(timing_info['process_method'].mean)
        }
        assert top_score_accuracy.value > 0.4
        assert any_accuracy.value > 0.4
        assert detection_recall.value > 0.65
