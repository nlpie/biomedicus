from pathlib import Path
from subprocess import PIPE, Popen

import pytest
from mtap import Pipeline, RemoteProcessor, events_client
from mtap.serialization import PickleSerializer
from mtap.utilities import find_free_port

from biomedicus import java_support


@pytest.fixture(name='normalization_processor')
def fixture_normalization_processor(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port

    with java_support.create_call(
            'edu.umn.biomedicus.normalization.NormalizationProcessor',
            '-p', port,
            '--events', events_service
    ) as call:
        p = Popen(call, start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        yield from processor_watcher(address, p, timeout=processor_timeout)


@pytest.mark.integration
def test_normalization(events_service, normalization_processor):
    pipeline = Pipeline(RemoteProcessor(
        name='biomedicus_normalizer',
        address=normalization_processor),
        events_address=events_service
    )
    with events_client(events_service) as client:
        with PickleSerializer.file_to_event(Path(__file__).parent / '97_95.pickle',
                                            client=client) as event:
            document = event.documents['plaintext']
            pipeline.run(document)
            for norm_form in document.labels['norm_forms']:
                if norm_form.text == "according":
                    assert norm_form.norm == "accord"
                if norm_form.text == "expressing":
                    assert norm_form.norm == "express"
                if norm_form.text == "receiving":
                    assert norm_form.norm == "receive"
                if norm_form.text == "days":
                    assert norm_form.norm == "day"
