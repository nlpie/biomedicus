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
import os
from pathlib import Path

import pytest
from mtap import metrics, EventsClient, Pipeline, RemoteProcessor, LocalProcessor
from mtap.io.serialization import PickleSerializer


@pytest.fixture(name='negation_service')
def fixture_negation_service(events_service, processor_watcher, processor_timeout):
    pass


@pytest.mark.skip(reason='There currently is not a Negation detector')
@pytest.mark.performance
def test_negation_performance(events_service, negation_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'negation' / 'i2b2_2010'
    confusion = metrics.FirstTokenConfusion()
    metrics_processor = metrics.Metrics(confusion, tested='negated', target='i2b2concepts',
                                        target_filter=lambda x: x.assertion == 'absent')
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor('biomedicus-negation', address=negation_service,
                            params={'terms_index': 'i2b2concepts'}),
            LocalProcessor(metrics_processor, component_id='metrics', client=client)
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                results = pipeline.run(document)
                print('F1 for event - "{}": {:0.3f} - elapsed: {}'.format(
                    event.event_id,
                    results[1].results['first_token_confusion']['f1'],
                    results[0].timing_info['process_method']
                ))

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats()[0].timing_info
        test_results['Negation'] = {
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Remote Call Duration': str(timing_info['remote_call'].mean),
            'Process Method Duration': str(timing_info['process_method'].mean)
        }
