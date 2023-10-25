import os
import sys
from subprocess import run, Popen, PIPE, STDOUT
from tempfile import TemporaryDirectory
from threading import Event, Thread

import pytest


@pytest.mark.performance
def test_scaleout(processor_timeout, test_data_dir):
    """Tests the default scaleout configurations"""
    # Copy descriptors to temporary directory
    with TemporaryDirectory() as tmpdir:
        result = run([sys.executable, "-m", "biomedicus", "write-config",
                      "scaleout_deploy", tmpdir])
        assert result.returncode == 0
        result = run([sys.executable, "-m", "biomedicus_client", "write-config",
                      "scaleout_pipeline", tmpdir])
        assert result.returncode == 0

        def listen(p, e=None):
            print("Starting listener", flush=True)
            for line in p.stdout:
                line = line.decode()
                print(line, end='', flush=True)
                if e is not None and line.startswith("Done deploying all servers."):
                    e.set()
            p.wait()
            if e is not None:
                e.set()

        deploy = None
        try:
            deploy = Popen([sys.executable, "-m", "biomedicus", "deploy",
                            "--noninteractive",
                            "--log-level", "DEBUG",
                            "--config", os.path.join(tmpdir, "scaleout_deploy.yml"),
                            "--startup-timeout", str(processor_timeout)],
                           stdout=PIPE, stderr=STDOUT)
            deploy_event = Event()
            deploy_listener = Thread(target=listen, args=(deploy, deploy_event))
            deploy_listener.start()
            deploy_event.wait(timeout=processor_timeout)
            if deploy.returncode is not None:
                raise ValueError("Failed to deploy.")

            input_folder = test_data_dir / "scaleout"
            output_folder = os.path.join(tmpdir, "output")
            process = run([sys.executable, "-m", "biomedicus_client", "run",
                           "--log-level", "DEBUG",
                           "--config", os.path.join(tmpdir, "scaleout_pipeline.yml"),
                           os.fspath(input_folder),
                           "-o", output_folder])
            assert process.returncode == 0
            f = os.listdir(output_folder)
            assert len(f) == sum(1 for _ in filter(lambda x: x.endswith('.txt'), os.listdir(input_folder)))
        finally:
            excs = []
            try:
                if deploy is not None:
                    deploy.terminate()
                    if deploy_listener is not None:
                        deploy_listener.join(timeout=10)
                        if deploy_listener.is_alive():
                            deploy.kill()
                            deploy_listener.join(timeout=10)
            except Exception as e:
                excs.append(e)

            if len(excs) > 0:
                raise ValueError("Failed to clean up pipeline", excs)
