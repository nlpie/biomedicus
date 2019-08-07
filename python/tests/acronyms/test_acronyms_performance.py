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
from pathlib import Path
from subprocess import Popen, TimeoutExpired

import grpc
import pytest
from nlpnewt.utils import find_free_port


@pytest.fixture(name='acronyms_service')
def fixture_acronyms_service(events_service):
    cwd = Path(__file__).parents[3] / 'java'
    port = str(find_free_port())
    address = '127.0.0.1:' + port
    p = Popen(['./gradlew', '-PmainClass=edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
               'execute', '--args=-p ' + port + ' --events ' + events_service])
    try:
        if p.returncode is not None:
            raise ValueError('subprocess terminated')
        with grpc.insecure_channel(address) as channel:
            future = grpc.channel_ready_future(channel)
            future.result(timeout=10)
        yield address
    finally:
        p.send_signal(signal.SIGINT)
        try:
            stdout, _ = p.communicate(timeout=1)
            print("python processor exited with code: ", p.returncode)
            print(stdout.decode('utf-8'))
        except TimeoutExpired:
            print("timed out waiting for python processor to terminate.")


@pytest.mark.performance
def test_acronyms_performance(events_service, acronyms_service):
    input_dir = Path(os.environ['BIOMEDICUS_TEST_DATA']) / 'acronyms'
