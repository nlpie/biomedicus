#  Copyright (c) Regents of the University of Minnesota.
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

import sys
import threading
import traceback
from contextlib import suppress
from subprocess import Popen, PIPE, STDOUT

import pytest


@pytest.fixture(name='deploy_all', scope='module')
def fixture_deploy_all(processor_timeout):
    p = None
    listener = None
    try:
        p = Popen([sys.executable, '-m', 'biomedicus', 'deploy', '--rtf',
                   '--noninteractive', '--log-level', 'DEBUG',
                   '--startup-timeout', str(processor_timeout)],
                  stdout=PIPE, stderr=STDOUT)
        e = threading.Event()

        def listen():
            print("Starting listener", flush=True)
            for line in p.stdout:
                line = line.decode()
                print(line, end='', flush=True)
                if line.startswith("Done deploying all servers."):
                    e.set()
            p.wait()
            e.set()

        listener = threading.Thread(target=listen)
        listener.start()
        e.wait(timeout=processor_timeout)
        if p.returncode is not None:
            raise ValueError("Failed to deploy.")
        print("Done starting deployment for tests, yielding to test functions.", flush=True)
        yield p
    finally:
        try:
            if p is not None:
                p.terminate()
                if listener is not None:
                    with suppress(TimeoutError):
                        listener.join(timeout=60.0)
                    if listener.is_alive():
                        p.kill()
                        listener.join(timeout=10.0)
        except Exception:
            print("Error cleaning up deployment")
            traceback.print_exc()
