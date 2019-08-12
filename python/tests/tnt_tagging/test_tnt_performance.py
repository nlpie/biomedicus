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
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired

import grpc
import pytest
import signal
from nlpnewt import Pipeline, RemoteProcessor, EventsClient, LocalProcessor
from nlpnewt.io.serialization import get_serializer
from nlpnewt.metrics import Metrics, Accuracy
from nlpnewt.utils import find_free_port
from pathlib import Path


@pytest.fixture(name='pos_tags_service')
def fixture_pos_tags_service(events_service):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = os.environ['BIOMEDICUS_JAR']
    p = Popen(['java', '-cp', biomedicus_jar,
               'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor', '-p', port,
               '--events', events_service],
              start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    try:
        if p.returncode is not None:
            raise ValueError('subprocess terminated')
        with grpc.insecure_channel(address) as channel:
            future = grpc.channel_ready_future(channel)
            future.result(timeout=10)
        yield address
    finally:
        p.send_signal(signal.SIGINT)
        try:
            stdout, _ = p.communicate(timeout=1)
            print("python processor exited with code: ", p.returncode)
            print(stdout.decode('utf-8'))
        except TimeoutExpired:
            print("timed out waiting for python processor to terminate")


@pytest.mark.performance
def test_tnt_performance(events_service, pos_tags_service):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'pos_tags'
    json_serializer = get_serializer('json')

    accuracy = Accuracy()
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor(processor_id='biomedicus-tnt-tagger', address=pos_tags_service,
                            params={'token_index': 'gold_tags'}),
            LocalProcessor(Metrics(accuracy, tested='pos_tags', target='gold_tags'),
                           component_id='metrics', client=client)
    ) as pipeline:
        for test_file in input_dir.glob('**/*.json'):
            event = json_serializer.file_to_event(test_file, client=client)
            with event:
                document = event['gold']
                results = pipeline.run(document)
                print('Accuracy for event - ', event.event_id, ':', results[1].results['accuracy'])

        print('Accuracy:', accuracy.value)
        pipeline.print_times()
        assert accuracy.value > 0.9
