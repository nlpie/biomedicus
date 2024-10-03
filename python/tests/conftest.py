# Copyright (c) Regents of the University of Minnesota.
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
import subprocess
from contextlib import suppress
from pathlib import Path
from threading import Thread

import grpc
import pytest
from mtap.utilities import subprocess_events_server


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration"
    )
    config.addinivalue_line(
        "markers", "performance"
    )
    config.addinivalue_line(
        "markers", "phi_performance"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--integration", action="store_true", default=False,
        help="Runs integration testing"
    )
    parser.addoption(
        "--performance", action="store_true", default=False,
        help="Runs performance testing",
    )
    parser.addoption(
        "--phi-performance", action="store_true", default=False,
        help="Runs performance tests which require the internal UMN PHI test data."
    )
    parser.addoption(
        "--timeout", type=float, default=20, help="The timeout for processors"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="need --integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
    if not config.getoption("--performance"):
        skip_consul = pytest.mark.skip(reason="need --performance option to run")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_consul)
    if not config.getoption("--phi-performance"):
        skip_phi_test_data = pytest.mark.skip(reason="need --phi-performance option to run")
        for item in items:
            if "phi_performance" in item.keywords:
                item.add_marker(skip_phi_test_data)


@pytest.fixture(name='processor_timeout', scope='session')
def fixture_processor_timeout(request):
    return request.config.getoption("--timeout")


@pytest.fixture(name='events_service')
def fixture_events_service():
    try:
        address = os.environ['EVENTS_ADDRESS']
        yield address
    except KeyError:
        with subprocess_events_server() as address:
            yield address


def _listen(process: subprocess.Popen):
    if process.stdout is None:
        return
    for line in process.stdout:
        print(line.decode(), end='')
    return process.wait()


@pytest.fixture(name='processor_watcher', scope='session')
def fixture_processor_watcher():
    def func(address, process, timeout=20):
        listener = Thread(target=_listen, args=(process,))
        listener.start()
        try:
            if process.returncode is not None:
                raise ValueError('subprocess terminated')
            with grpc.insecure_channel(address, [('grpc.enable_http_proxy', False)]) as channel:
                future = grpc.channel_ready_future(channel)
                future.result(timeout=timeout)
            yield address
        finally:
            try:
                process.terminate()
                with suppress(TimeoutError):
                    listener.join(timeout=5.0)
                if listener.is_alive():
                    process.kill()
                    listener.join()
                print("processor exited with code: ", process.returncode)
            except Exception:
                pass

    return func


@pytest.fixture(name='test_results', scope='session')
def fixture_test_results():
    results = {}
    yield results
    import yaml
    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper
    with open('test_results.yml', 'w') as f:
        yaml.dump(results, f, Dumper=Dumper)


@pytest.fixture(name='test_data_dir', scope='session')
def fixture_test_data_dir():
    try:
        return Path(os.environ['BIOMEDICUS_TEST_DATA'])
    except KeyError:
        pytest.fail("Missing required environment variable BIOMEDICUS_TEST_DATA")
