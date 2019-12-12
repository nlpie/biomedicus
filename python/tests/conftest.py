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
import signal
import subprocess
import sys

import grpc
import pytest
from mtap.utilities import subprocess_events_server


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "performance"
    )
    config.addinivalue_line(
        "markers", "phi_test_data"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--performance", action="store_true", default=False,
        help="Runs performance testing",
    )
    parser.addoption(
        "--phi-test-data", action="store_true", default=False,
        help="Runs tests which require the internal UMN PHI test data."
    )
    parser.addoption(
        "--timeout", type=float, default=20, help="The timeout for processors"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--performance"):
        skip_consul = pytest.mark.skip(reason="need --performance option to run")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_consul)
    if not config.getoption("--phi-test-data"):
        skip_phi_test_data = pytest.mark.skip(reason="need --phi-test-data option to run")
        for item in items:
            if "phi_test_data" in item.keywords:
                item.add_marker(skip_phi_test_data)


@pytest.fixture(name='processor_timeout')
def fixture_processor_timeout(request):
    return request.config.getoption("--timeout")


@pytest.fixture(name='events_service')
def fixture_events_service():
    with subprocess_events_server() as address:
        yield address


@pytest.fixture(name='processor_watcher')
def fixture_processor_watcher():
    def func(address, process, timeout=20):
        try:
            if process.returncode is not None:
                raise ValueError('subprocess terminated')
            with grpc.insecure_channel(address) as channel:
                future = grpc.channel_ready_future(channel)
                future.result(timeout=timeout)
            yield address
        finally:
            process.send_signal(signal.SIGINT)
            try:
                stdout, stderr = process.communicate(timeout=1)
                print("processor exited with code: ", process.returncode)
                if stdout is not None:
                    print(stdout.decode('utf-8'))
                if stderr:
                    print(stderr.decode('utf-8'), file=sys.stderr)
            except subprocess.TimeoutExpired:
                print("timed out waiting for processor to terminate")
    return func
