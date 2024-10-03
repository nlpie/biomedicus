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

import base64
import sys
import tempfile
import time
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired

import pytest
import requests
import yaml
from mtap.utilities import find_free_port
from requests import RequestException, Session

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper


text = (Path(__file__).parent / 'rtf_in' / '97_204.rtf').read_bytes()


@pytest.fixture(name='hosted_pipeline')
def fixture_hosted_pipeline(deploy_all, processor_watcher):
    port = find_free_port()
    p = Popen([sys.executable, '-m', 'biomedicus', 'serve-pipeline', '--port', str(port), '--rtf'])
    yield from processor_watcher(f'127.0.0.1:{port}', p)

    
@pytest.fixture(name='rtf_to_text_pipeline')
def fixture_rtf_to_text_pipeline(deploy_all, processor_watcher):
    port = find_free_port()
    p = Popen([sys.executable, '-m', 'biomedicus', 'serve-rtf-to-text', '--port', str(port)])
    yield from processor_watcher(f'127.0.0.1:{port}', p)


@pytest.fixture(name='mtap_gateway')
def fixture_mtap_gateway(hosted_pipeline, rtf_to_text_pipeline):
    port = find_free_port()
    config = {
        'discovery': 'consul',
        'grpc': {
            'enable_proxy': False
        },

        'max_send_message_length': 104857600,
        'max_receive_message_length': 104857600,
        'consul': {
            'host': 'localhost',
            'port': 8500,
            'scheme': 'http',
            # Python uses {python_naming_scheme}:address[:port][,address[:port],...] as grpc targets
            'python_naming_scheme': 'ipv4'
        },
        'gateway': {
            'port': port,
            'refresh_interval': 10,
            'events': '127.0.0.1:50100',
            'pipelines': [
                {
                    'Identifier': 'biomedicus-default-pipeline',
                    'Endpoint': hosted_pipeline
                },
                {
                    'Identifier': 'biomedicus-rtf-to-text',
                    'Endpoint': rtf_to_text_pipeline
                }
            ]
        }
    }

    with tempfile.NamedTemporaryFile('w', suffix='.yml') as conf_file:
        yaml.dump(config, conf_file, Dumper=Dumper)
        conf_file.flush()
        p = Popen(['mtap-gateway', '-logtostderr', '-v=3',
                   '-mtap-config=' + conf_file.name],
                  stdin=PIPE, stdout=PIPE, stderr=STDOUT)

        session = Session()
        session.trust_env = False
        gateway = '127.0.0.1:{}'.format(port)
        try:
            if p.returncode is not None:
                raise ValueError("Failed to launch go gateway")
            for i in range(6):
                if i == 5:
                    raise ValueError("Failed to connect to go gateway")
                try:
                    time.sleep(3)
                    resp = session.get(
                        "http://{}/v1/processors".format(gateway), timeout=1)
                    if resp.status_code == 200 and len(resp.json()['Processors']) == 0:
                        break
                except RequestException:
                    pass
            yield gateway
        finally:
            session.close()
            p.terminate()
            try:
                stdout, _ = p.communicate(timeout=1)
                print("api gateway exited with code: ", p.returncode)
                print(stdout.decode('utf-8'))
            except TimeoutExpired:
                print("timed out waiting for api gateway to terminate")
                p.kill()
                stdout, _ = p.communicate(timeout=1)
                print("api gateway exited with code: ", p.returncode)
                print(stdout.decode('utf-8'))


@pytest.mark.integration
def test_rest_e2e(mtap_gateway):
    session = requests.Session()
    session.trust_env = False
    base_url = "http://" + mtap_gateway

    body = {
        'event': {
            'event_id': '1.txt',
            'binaries': {
                'rtf': base64.standard_b64encode(text).decode('utf-8')
            }
        },
        'params': {
            'document_name': 'plaintext',
        }
    }
    resp = session.post(
        base_url + '/v1/pipeline/biomedicus-default-pipeline/process',
        json=body,
        timeout=10
    )
    assert resp.status_code == 200
    resp_body = resp.json()
    label_indices = resp_body['event']['documents']['plaintext']['label_indices']
    assert len(label_indices) > 0


@pytest.mark.integration
def test_rest_rtf(mtap_gateway):
    session = requests.Session()
    session.trust_env = False
    base_url = "http://" + mtap_gateway

    body = {
        'event': {
            'event_id': '1.txt',
            'binaries': {
                'rtf': base64.standard_b64encode(text).decode('utf-8')
            }
        },
        'params': {
            'document_name': 'plaintext',
        }
    }
    resp = session.post(
        base_url + '/v1/pipeline/biomedicus-rtf-to-text/process',
        json=body,
        timeout=10
    )
    assert resp.status_code == 200
    resp_body = resp.json()
    assert len(resp_body['event']['documents']['plaintext']['text']) > 0
