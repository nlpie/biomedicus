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
from subprocess import PIPE, Popen

import pytest
from nlpnewt.utils import find_free_port

from tests.pytest import handle_service_process


@pytest.fixture(name='fixture_normalization_processor')
def normalization_processor(events_service):
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    biomedicus_jar = os.environ['BIOMEDICUS_JAR']
    p = Popen(['java', '-cp', biomedicus_jar, 'edu.umn.biomedicus.normalization.NormalizationProcessor',
               '-p', port, '--events', events_service],
              start_new_session=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    yield from handle_service_process(address, p)


