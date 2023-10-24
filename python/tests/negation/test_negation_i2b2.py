import os
import re
import sys
from subprocess import Popen, PIPE, STDOUT

import pytest
from mtap import metrics, Pipeline, RemoteProcessor, LocalProcessor, GenericLabel, events_client
from mtap.serialization import PickleSerializer
from mtap.utilities import find_free_port

from biomedicus.java_support import create_call

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
    p = Popen([sys.executable, '-m', 'biomedicus.negation.negex', '-p', port, '--events', events_service],
              stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


@pytest.fixture(name='negex_triggers_service')
def fixture_negex_triggers_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = Popen([sys.executable, '-m', 'biomedicus.negation.negex_triggers', '-p', port, '--events',
               events_service],
              stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


@pytest.fixture(name='modification_detector_service')
def fixture_modification_detector_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    with create_call(
            'edu.umn.biomedicus.modification.ModificationDetector',
            '-p', port,
            '--events', events_service
    ) as call:
        p = Popen(call, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
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
    p = Popen([sys.executable, '-m', 'biomedicus.dependencies.stanza_selective_parser',
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
        [sys.executable, '-m', 'biomedicus.negation.deepen', '-p', port, '--events', events_service],
        stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    yield from processor_watcher(address, p, processor_timeout)


def is_negated(term: GenericLabel) -> bool:
    if term.assertion == 'absent':
        lower = _not_word.sub('', term.text.lower().split()[0])
        if lower not in self_negated:
            return True
    return False


def run_and_report(name, pipeline, events_service, test_results, test_data_dir):
    input_dir = test_data_dir / 'negation' / 'i2b2_2010'
    confusion = metrics.FirstTokenConfusion(print_debug='fn', debug_range=120)
    metrics_processor = metrics.Metrics(confusion, tested='negated', target='i2b2concepts',
                                        target_filter=is_negated)
    pipeline.append(LocalProcessor(metrics_processor))
    with events_client(events_service) as client:
        times = pipeline.create_times()
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                result = pipeline.run(document)
                times.add_result_times(result)
                f1 = result.component_result('mtap-metrics').result_dict['first_token_confusion']['f1']
                print(f'F1 for event - "{event.event_id}": {f1:0.3f}')

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        times.print()
        stats = times.aggregate_timer_stats()
        test_results[name] = {
            'Gold Standard': "2010 i2b2-VA",
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Per-Document Mean Pipeline Duration': str(stats.timing_info['total'].mean),
        }


@pytest.mark.performance
def test_negex_performance(events_service, negex_service, test_results, test_data_dir):
    pipeline = Pipeline(
        RemoteProcessor('biomedicus-negation', address=negex_service,
                        params={'terms_index': 'i2b2concepts'}),
        events_address=events_service
    )
    run_and_report('biomedicus-negex', pipeline, events_service, test_results, test_data_dir)


@pytest.mark.performance
def test_modification_detector_performance(events_service, modification_detector_service,
                                           test_results, test_data_dir):
    pipeline = Pipeline(
        RemoteProcessor('biomedicus-negation', address=modification_detector_service,
                        params={'terms_index': 'i2b2concepts'}),
        events_address=events_service
    )
    run_and_report('biomedicus-modification', pipeline, events_service, test_results, test_data_dir)


@pytest.mark.performance
def test_deepen_performance(events_service, negex_triggers_service, dependencies_service,
                            deepen_negation_service, test_results, test_data_dir):
    pipeline = Pipeline(
        RemoteProcessor(name='biomedicus-negex-triggers',
                        address=negex_triggers_service),
        RemoteProcessor(name='biomedicus-selective-dependencies',
                        address=dependencies_service,
                        params={'terms_index': 'i2b2concepts'}),
        RemoteProcessor('biomedicus-deepen', address=deepen_negation_service,
                        params={'terms_index': 'i2b2concepts'}),
        events_address=events_service
    )
    run_and_report('biomedicus-deepen', pipeline, events_service, test_results, test_data_dir)
