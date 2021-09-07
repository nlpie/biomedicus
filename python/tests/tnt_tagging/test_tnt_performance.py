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
from subprocess import PIPE, STDOUT, Popen

import pytest
from mtap import Pipeline, RemoteProcessor, EventsClient, LocalProcessor
from mtap.io.serialization import PickleSerializer
from mtap.metrics import Metrics, Accuracy
from mtap.utilities import find_free_port

import biomedicus


@pytest.fixture(name='pos_tags_service')
def fixture_pos_tags_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = biomedicus.biomedicus_jar()
    p = Popen(['java', '-cp', biomedicus_jar,
               'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor', '-p', port,
               '--events', events_service],
              start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.performance
def test_tnt_performance(events_service, pos_tags_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'pos_tags'
    accuracy = Accuracy()
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor(processor_id='biomedicus-tnt-tagger', address=pos_tags_service,
                            params={'token_index': 'gold_tags'}),
            LocalProcessor(Metrics(accuracy, tested='pos_tags', target='gold_tags'),
                           component_id='metrics'),
            events_client=client
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            event = PickleSerializer.file_to_event(test_file, client=client)
            with event:
                document = event.documents['gold']
                results = pipeline.run(document)
                print('Accuracy for event - ', event.event_id, ':',
                      results.component_result('metrics').result_dict['accuracy'])

        print('Accuracy:', accuracy.value)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats('biomedicus-tnt-tagger').timing_info
        test_results['TnT Pos Tagger'] = {
            'Accuracy': accuracy.value,
            'Remote Call Duration': str(timing_info['remote_call'].mean),
            'Process Method Duration': str(timing_info['process_method'].mean)
        }
        assert accuracy.value > 0.9
