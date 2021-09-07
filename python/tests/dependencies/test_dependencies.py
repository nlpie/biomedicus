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
import subprocess
from pathlib import Path

import pytest
from mtap import EventsClient, Pipeline, RemoteProcessor, LocalProcessor
from mtap.io.serialization import PickleSerializer
from mtap.metrics import Accuracy, Metrics
from mtap.utilities import find_free_port


@pytest.fixture(name='dependencies_service')
def fixture_dependencies_service(events_service, processor_watcher, processor_timeout):
    try:
        existing_address = os.environ['DEPENDENCIES_ADDRESS']
        yield existing_address
        return
    except KeyError:
        pass
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = subprocess.Popen(['python', '-m', 'biomedicus.dependencies.stanza_parser',
                          '-p', port,
                          '--events', events_service],
                         start_new_session=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    yield from processor_watcher(address, p, timeout=processor_timeout)


def uas_equal(x, y):
    if x.head is None and y.head is None:
        return True
    if x.head is None or y.head is None:
        return False
    return x.head.location == y.head.location


def las_equal(x, y):
    return uas_equal(x, y) and x.deprel == y.deprel


@pytest.mark.performance
def test_dependencies(events_service, dependencies_service, test_results):
    test_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'dependencies'
    uas = Accuracy('UAS', equivalence_test=uas_equal)
    las = Accuracy('LAS', equivalence_test=las_equal)
    with EventsClient(address=events_service) as client, \
            Pipeline(
                RemoteProcessor(processor_id='biomedicus-dependencies',
                                address=dependencies_service),
                LocalProcessor(Metrics(uas, las, tested='dependencies', target='gold_dependencies'),
                               component_id='accuracy'),
                events_client=client
            ) as pipeline:
        for test_file in test_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                results = pipeline.run(document)
                accuracy_dict = results.component_result('accuracy').result_dict
                print('Results for document: UAS: {}. LAS: {}.'.format(accuracy_dict['UAS'],
                                                                       accuracy_dict['LAS']))

    print('UAS:', uas.value)
    print('LAS:', las.value)
    timing_info = pipeline.processor_timer_stats('biomedicus-dependencies').timing_info
    test_results['biomedicus-dependencies'] = {
        'UAS': uas.value,
        'LAS': las.value,
        'Corpus': "MiPACQ converted to UD from PTB test set",
        'Remote Call Duration': str(timing_info['remote_call'].mean),
        'Process Method Duration': str(timing_info['process_method'].mean)
    }
