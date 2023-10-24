import os
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT

import pytest
from mtap import Pipeline, RemoteProcessor, LocalProcessor, events_client
from mtap.metrics import Accuracy, Metrics
from mtap.serialization import JsonSerializer
from mtap.utilities import find_free_port

from biomedicus.java_support import create_call


@pytest.fixture(name='acronyms_service')
def fixture_acronyms_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    with create_call('edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
                     '-p', port,
                     '--events', events_service) as call:
        p = Popen(call, start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.phi_performance
def test_acronyms_performance(events_service, acronyms_service, test_results):
    try:
        input_dir = Path(os.environ['BIOMEDICUS_PHI_TEST_DATA']) / 'acronyms'
    except KeyError:
        pytest.fail("Missing required environment variable BIOMEDICUS_PHI_TEST_DATA")
    top_score_accuracy = Accuracy(name='top_score_accuracy', fields=['expansion'])
    any_accuracy = Accuracy(name='any_accuracy', mode='any', fields=['expansion'])
    detection_recall = Accuracy(name='detection_recall', mode='location', fields=['expansion'])
    detection_precision = Accuracy(name='detection_precision', mode='location',
                                   fields=['expansion'])
    pipeline = Pipeline(
            RemoteProcessor(name='biomedicus-acronyms', address=acronyms_service),
            LocalProcessor(Metrics(top_score_accuracy, detection_recall, tested='acronyms',
                                   target='gold_acronyms'),
                           component_id='top_score_metrics'),
            LocalProcessor(Metrics(detection_precision, tested='gold_acronyms', target='acronyms'),
                           component_id='top_score_reverse'),
            LocalProcessor(Metrics(any_accuracy, tested='all_acronym_senses', target='gold_acronyms'),
                           component_id='all_senses_metrics'),
            events_address=events_service
    )
    with events_client(events_service) as client:
        times = pipeline.create_times()
        for test_file in input_dir.glob('**/*.json'):
            with JsonSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']
                result = pipeline.run(document)
                times.add_result_times(result)

        print('Top Sense Accuracy:', top_score_accuracy.value)
        print('Any Sense Accuracy:', any_accuracy.value)
        print('Detection Recall:', detection_recall.value)
        print('Detection Precision:', detection_precision.value)
        timing_info = times.processor_timer_stats('biomedicus-acronyms').timing_info
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
