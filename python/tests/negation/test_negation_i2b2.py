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
import re
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT

import pytest
from mtap import metrics, EventsClient, Pipeline, RemoteProcessor, LocalProcessor, GenericLabel
from mtap.io.serialization import PickleSerializer
from mtap.utilities import find_free_port

import biomedicus

_not_word = re.compile(r'[^\w/\-]+')

self_negated = {
    'non-distended',
    'nondistended',
    'non-tender',
    'nontender',
    'nc',
    'nt',
    'nd',
    'anicteric',
    'anicterus',
    'afebrile',
    'atraumatic',
    'noncyanotic',
    'nad',
    'nka',
    'nondysmorphic',
    'unlabored',
    'non',
    'unresponsive',
    'nc/at',
    'nabs',
    'asymptomatic',
    'nonicteric',
    's/nt/nd',
    'nt/nd/+bs',
    'ngtd',
    'nt/nd',
    'nonedematous',
    'non-icteric',
    'uncomplicated',
    'assymptomatic',
    'nonradiating',
    'uninfected',
    'noparoxysmal',
    'nonparoxysmal',
    'non-',
    'non-elavated',
    'nt,nd'
}


@pytest.fixture(name='negex_service')
def fixture_negex_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = Popen(['python', '-m', 'biomedicus.negation.negex', '-p', port, '--events', events_service],
              stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


@pytest.fixture(name='negex_triggers_service')
def fixture_negex_triggers_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = Popen(['python', '-m', 'biomedicus.negation.negex_triggers', '-p', port, '--events',
               events_service],
              stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


@pytest.fixture(name='modification_detector_service')
def fixture_modification_detector_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = biomedicus.biomedicus_jar()
    p = Popen(['java', '-cp', biomedicus_jar,
               'edu.umn.biomedicus.modification.ModificationDetector', '-p', port,
               '--events', events_service], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, timeout=processor_timeout)


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
    p = Popen(['python', '-m', 'biomedicus.dependencies.stanza_selective_parser',
               '-p', port,
               '--events', events_service],
              start_new_session=True, stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.fixture(name='deepen_negation_service')
def fixture_deepen_negation_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = Popen(
        ['python', '-m', 'biomedicus.negation.deepen', '-p', port, '--events', events_service],
        stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


def is_negated(term: GenericLabel) -> bool:
    if term.assertion == 'absent':
        lower = _not_word.sub('', term.text.lower().split()[0])
        if lower not in self_negated:
            return True
    return False


@pytest.mark.performance
def test_negex_performance(events_service, negex_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'negation' / 'i2b2_2010'
    confusion = metrics.FirstTokenConfusion(print_debug='fn', debug_range=120)
    metrics_processor = metrics.Metrics(confusion, tested='negated', target='i2b2concepts',
                                        target_filter=is_negated)
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor('biomedicus-negation', address=negex_service,
                            params={'terms_index': 'i2b2concepts'}),
            LocalProcessor(metrics_processor, component_id='metrics'),
            events_client=client
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                results = pipeline.run(document)
                print('F1 for event - "{}": {:0.3f} - elapsed: {}'.format(
                    event.event_id,
                    results.component_result('metrics').result_dict['first_token_confusion']['f1'],
                    results.component_result('biomedicus-negation').timing_info['process_method']
                ))

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats('biomedicus-negation').timing_info
        test_results['biomedicus-negex'] = {
            'Gold Standard': "2010 i2b2-VA",
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Per-Document Mean Remote Call Duration': str(timing_info['remote_call'].mean),
            'Per-Document Mean Process Method Duration': str(timing_info['process_method'].mean)
        }


@pytest.mark.performance
def test_modification_detector_performance(events_service, modification_detector_service,
                                           test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'negation' / 'i2b2_2010'
    confusion = metrics.FirstTokenConfusion()
    metrics_processor = metrics.Metrics(confusion, tested='negated', target='i2b2concepts',
                                        target_filter=is_negated)
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor('biomedicus-negation', address=modification_detector_service,
                            params={'terms_index': 'i2b2concepts'}),
            LocalProcessor(metrics_processor, component_id='metrics'),
            events_client=client
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                results = pipeline.run(document)
                print('F1 for event - "{}": {:0.3f} - elapsed: {}'.format(
                    event.event_id,
                    results.component_result('metrics').result_dict['first_token_confusion']['f1'],
                    results.component_result('biomedicus-negation').timing_info['process_method']
                ))

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats('biomedicus-negation').timing_info
        test_results['biomedicus-modification'] = {
            'Gold Standard': "2010 i2b2-VA",
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Per-Document Mean Remote Call Duration': str(timing_info['remote_call'].mean),
            'Per-Document Mean Process Method Duration': str(timing_info['process_method'].mean)
        }


@pytest.mark.performance
def test_deepen_performance(events_service, negex_triggers_service, dependencies_service,
                            deepen_negation_service, test_results):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'negation' / 'i2b2_2010'
    confusion = metrics.FirstTokenConfusion()
    metrics_processor = metrics.Metrics(confusion, tested='negated', target='i2b2concepts',
                                        target_filter=is_negated)
    with EventsClient(address=events_service) as client, Pipeline(
            RemoteProcessor(processor_id='biomedicus-negex-triggers',
                            address=negex_triggers_service),
            RemoteProcessor(processor_id='biomedicus-selective-dependencies',
                            address=dependencies_service,
                            params={'terms_index': 'i2b2concepts'}),
            RemoteProcessor('biomedicus-deepen', address=deepen_negation_service,
                            params={'terms_index': 'i2b2concepts'}),
            LocalProcessor(metrics_processor, component_id='metrics'),
            events_client=client
    ) as pipeline:
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                results = pipeline.run(document)
                print('F1 for event - "{}": {:0.3f} - elapsed: {}'.format(
                    event.event_id,
                    results.component_result('metrics').result_dict['first_token_confusion']['f1'],
                    results.component_result('biomedicus-selective-dependencies').timing_info[
                        'process_method']
                ))

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        pipeline.print_times()
        timing_info = pipeline.processor_timer_stats('biomedicus-deepen').timing_info
        timing_info_parse = pipeline.processor_timer_stats(
            'biomedicus-selective-dependencies').timing_info
        test_results['biomedicus-deepen'] = {
            'Gold Standard': "2010 i2b2-VA",
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Per-Document Mean Remote Call Duration': str(
                timing_info['remote_call'].mean + timing_info_parse['remote_call'].mean),
            'Per-Document Mean Process Method Duration': str(
                timing_info['process_method'].mean + timing_info_parse['process_method'].mean)
        }
