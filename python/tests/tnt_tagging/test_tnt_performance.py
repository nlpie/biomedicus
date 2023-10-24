import os
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

import pytest
from mtap import Pipeline, RemoteProcessor, LocalProcessor, events_client
from mtap.metrics import Metrics, Accuracy
from mtap.serialization import PickleSerializer
from mtap.utilities import find_free_port

from biomedicus.java_support import create_call


@pytest.fixture(name='pos_tags_service')
def fixture_pos_tags_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    with create_call(
            'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor',
            '-p', port,
            '--events', events_service
    ) as call:
        p = Popen(call, start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.performance
def test_tnt_performance(events_service, pos_tags_service, test_results):
    try:
        input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'pos_tags'
    except KeyError:
        pytest.fail("Missing required environment variable BIOMEDICUS_TEST_DATA")
    accuracy = Accuracy()
    pipeline = Pipeline(
        RemoteProcessor(name='biomedicus-tnt-tagger', address=pos_tags_service,
                        params={'token_index': 'gold_tags'}),
        LocalProcessor(Metrics(accuracy, tested='pos_tags', target='gold_tags'), component_id='metrics'),
        events_address=events_service
    )
    with events_client(events_service) as client:
        times = pipeline.create_times()
        for test_file in input_dir.glob('**/*.pickle'):
            with PickleSerializer.file_to_event(test_file, client=client) as e:
                document = e.documents['gold']
                result = pipeline.run(document)
                times.add_result_times(result)
                print(
                    'Accuracy for event - ',
                    document.event.event_id, ':',
                    result.component_result('metrics').result_dict['accuracy']
                )

        print('Accuracy:', accuracy.value)
        times.print()
        timing_info = times.processor_timer_stats('biomedicus-tnt-tagger').timing_info
        test_results['TnT Pos Tagger'] = {
            'Accuracy': accuracy.value,
            'Remote Call Duration': str(timing_info['remote_call'].mean),
            'Process Method Duration': str(timing_info['process_method'].mean)
        }
        assert accuracy.value > 0.9
