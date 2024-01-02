import os
import sys
import threading
import traceback
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT, run
from tempfile import TemporaryDirectory

import pytest
from mtap.serialization import JsonSerializer


@pytest.fixture(name='deploy_all')
def fixture_deploy_all(processor_timeout):
    p = None
    listener = None
    try:
        p = Popen([sys.executable, '-m', 'biomedicus', 'deploy', '--rtf', '--noninteractive', '--log-level', 'DEBUG',
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
                    listener.join(timeout=60.0)
                    if listener.is_alive():
                        p.kill()
                        listener.join()
        except Exception:
            print("Error cleaning up deployment")
            traceback.print_exc()


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
