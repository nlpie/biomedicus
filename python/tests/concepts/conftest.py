from subprocess import Popen, PIPE

import pytest
from mtap.utilities import find_free_port

from biomedicus.java_support import create_call


@pytest.fixture(name='concepts_service')
def fixture_concepts_service(events_service, processor_watcher, processor_timeout):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    with create_call(
        'edu.umn.biomedicus.concepts.DictionaryConceptDetector',
        '-p', port,
        '--events', events_service
    ) as call:
        p = Popen(call, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        yield from processor_watcher(address, p, timeout=processor_timeout)
