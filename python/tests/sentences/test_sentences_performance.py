import os
import subprocess
from pathlib import Path

import pytest
from mtap import Pipeline, RemoteProcessor, LocalProcessor, events_client
from mtap import metrics
from mtap.serialization import JsonSerializer
from mtap.utilities import find_free_port


@pytest.fixture(name='sentences_service')
def fixture_sentences_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = subprocess.Popen(['python', '-m', 'biomedicus.sentences.bi_lstm', 'processor',
                          '-p', port,
                          '--events', events_service],
                         start_new_session=True, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.phi_performance
def test_sentence_performance(events_service, sentences_service, test_results):
    try:
        input_dir = Path(os.environ['BIOMEDICUS_PHI_TEST_DATA']) / 'sentences'
    except KeyError:
        pytest.fail('Missing required environment variable BIOMEDICUS_PHI_TEST_DATA')

    confusion = metrics.FirstTokenConfusion()
    pipeline = Pipeline(
        RemoteProcessor(name='biomedicus-sentences', address=sentences_service),
        LocalProcessor(metrics.Metrics(confusion, tested='sentences', target='Sentence'), component_id='metrics'),
        events_address=events_service
    )
    with events_client(events_service) as client:
        times = pipeline.create_times()
        for test_file in input_dir.glob('**/*.json'):
            with JsonSerializer.file_to_event(test_file, client=client) as event:
                document = event.documents['plaintext']

                result = pipeline.run(document)
                times.add_result_times(result)
                print('F1 for event - "{}": {:0.3f} - elapsed: {}'.format(
                    event.event_id,
                    result.component_result('metrics').result_dict['first_token_confusion']['f1'],
                    result.component_result('biomedicus-sentences').timing_info['process_method'])
                )

        print('Overall Precision:', confusion.precision)
        print('Overall Recall:', confusion.recall)
        print('Overall F1:', confusion.f1)
        times.print()
        timing_info = times.processor_timer_stats('biomedicus-sentences').timing_info
        test_results['biomedicus-sentences'] = {
            'Precision': confusion.precision,
            'Recall': confusion.recall,
            'F1': confusion.f1,
            'Remote Call Duration': str(timing_info['remote_call'].mean),
            'Process Method Duration': str(timing_info['process_method'].mean)
        }
        assert confusion.f1 > 0.85
