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

import os
import sys
from pathlib import Path
from subprocess import PIPE, STDOUT, run
from tempfile import TemporaryDirectory

import pytest
from mtap.serialization import JsonSerializer


@pytest.mark.integration
def test_deploy_run(deploy_all, processor_timeout):
    print("testing deployment run", flush=True)
    with TemporaryDirectory() as tmpdir:
        input_folder = os.fspath((Path(__file__).parent / 'in').absolute())
        cp = run([sys.executable,
                  '-m', 'biomedicus_client',
                  'run', input_folder,
                  '-o', tmpdir,
                  '--log-level', 'DEBUG'],
                 timeout=processor_timeout, stdout=PIPE, stderr=STDOUT)
        print(cp.stdout.decode('utf-8'), end='')
        assert cp.returncode == 0
        with JsonSerializer.file_to_event(Path(tmpdir) / '97_204.txt.json') as event:
            document = event.documents['plaintext']
            assert len(document.labels['sentences']) > 0
            assert len(document.labels['pos_tags']) > 0
            assert len(document.labels['acronyms']) > 0
            assert len(document.labels['umls_concepts']) > 0


@pytest.mark.integration
def test_deploy_run_rtf(deploy_all, processor_timeout):
    print("testing rtf deployment run", flush=True)
    with TemporaryDirectory() as tmpdir:
        input_folder = os.fspath((Path(__file__).parent / 'rtf_in').absolute())
        cp = run([sys.executable, '-m', 'biomedicus_client', 'run', input_folder, '--rtf', '-o', tmpdir,
                  '--log-level', 'DEBUG'],
                 timeout=processor_timeout, stdout=PIPE, stderr=STDOUT)
        print(cp.stdout.decode('utf-8'), end='')
        assert cp.returncode == 0
        with JsonSerializer.file_to_event(Path(tmpdir) / '97_204.rtf.json') as event:
            document = event.documents['plaintext']
            assert len(document.labels['sentences']) > 0
            assert len(document.labels['pos_tags']) > 0
            assert len(document.labels['acronyms']) > 0
            assert len(document.labels['umls_concepts']) > 0
