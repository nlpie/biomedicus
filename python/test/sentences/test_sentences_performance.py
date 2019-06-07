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
import signal
import subprocess
from pathlib import Path

import grpc
import pytest
from nlpnewt import Events, Pipeline
from nlpnewt.io.serialization import get_serializer
from nlpnewt.metrics import Metrics, Accuracy
from nlpnewt.utils import find_free_port


@pytest.fixture(name='sentences_service')
def fixture_sentences_service(events_service):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = subprocess.Popen(['python', '-m', 'biomedicus.sentences',
                          'processor',
                          '-p', port,
                          '--events', events_service],
                         start_new_session=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        if p.returncode is not None:
            raise ValueError('subprocess terminated')
        with grpc.insecure_channel(address) as channel:
            future = grpc.channel_ready_future(channel)
            future.result(timeout=120)
        yield address
    finally:
        p.send_signal(signal.SIGINT)
        try:
            stdout, _ = p.communicate(timeout=1)
            print("python processor exited with code: ", p.returncode)
            print(stdout.decode('utf-8'))
        except subprocess.TimeoutExpired:
            print("timed out waiting for python processor to terminate")


@pytest.mark.performance
def test_sentence_performance(events_service, sentences_service):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'sentences'
    json_serializer = get_serializer('json')

    accuracy = Accuracy()
    with Events(address=events_service) as events, Pipeline() as pipeline:
        pipeline.add_processor(name='biomedicus-sentences', address=sentences_service)
        pipeline.add_local_processor(Metrics(accuracy, tested='sentences', target='Sentence'),
                                     identifier='metrics', events=events)
        for test_file in input_dir.glob('**/*.json'):
            event = json_serializer.file_to_event(test_file, events=events)
            with event:
                document = event['plaintext']
                results = pipeline.run(document)
                print('Accuracy for event - ', event.event_id, ':', results[1].results['accuracy'])

        print('Accuracy:', accuracy.value)
        pipeline.print_times()
        assert accuracy.value > 0.8
