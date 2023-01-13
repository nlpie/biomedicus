import shutil
from pathlib import Path
from subprocess import Popen, STDOUT, call, PIPE

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


def build_java():
    """Builds the java source code and includes the jar with the python modules.
    """
    wkdir = Path(__file__).parent
    cwd = wkdir / 'java'
    if cwd.exists():
        p = Popen(['./gradlew', 'build', 'shadowJar'], cwd=str(cwd), stdout=PIPE, stderr=STDOUT)
        for line in p.stdout:
            print(line.decode(), end='')
        return_code = p.wait()
        if return_code:
            raise IOError('Java build failed.')
        call(['./gradlew', 'writeVersion'], cwd=str(cwd))
        with (cwd / 'build' / 'version.txt').open('r') as f:
            version = f.read()[:-1]
        jar_file = cwd / 'build' / 'libs' / ('biomedicus-' + version + '-all.jar')
        jar_out = wkdir / 'python' / 'biomedicus' / 'biomedicus-all.jar'
        shutil.copy2(str(jar_file), str(jar_out))


class build_py(_build_py):
    def run(self):
        build_java()
        return super().run()


setup(
    cmdclass={
        "build_py": build_py
    },
    include_package_data=True,
    package_data={'biomedicus': ['biomedicus-all.jar']}
)
