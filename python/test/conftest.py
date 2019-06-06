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

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "performance"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--performance", action="store_true", default=False,
        help="Runs performance testing",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--performance"):
        skip_consul = pytest.mark.skip(reason="need --performance option to run")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_consul)

@pytest.fixture(name='events_service')
def fixture_events_service():
    with subprocess_events_server(cwd=Path(__file__).parents[2],
                                  config_path=config_path) as address:
        yield address
