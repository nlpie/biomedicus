"""A biomedical and clinical NLP engine developed by the University of
Minnesota NLP/IE Group."""
import shutil
import sys
from pathlib import Path
from subprocess import call, Popen, STDOUT, PIPE

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.test import test as _test


def build_java():
    """Builds the java source code and includes the jar with the python modules.
    """
    cwd = Path(__file__).parent / 'java'
    if cwd.exists():
        p = Popen(['./gradlew', 'build', 'shadowJar'], cwd=str(cwd), stdout=PIPE,
                  stderr=STDOUT)
        for line in p.stdout:
            print(line.decode(), end='')
        return_code = p.wait()
        if return_code:
            raise IOError('Java build failed.')
        call(['./gradlew', 'writeVersion'], cwd=str(cwd))
        with (cwd / 'build' / 'version.txt').open('r') as f:
            version = f.read()[:-1]
        jar_file = cwd / 'build' / 'libs' / ('biomedicus-' + version + '-all.jar')
        jar_out = Path(__file__).parent / 'python' / 'biomedicus' / 'biomedicus-all.jar'
        shutil.copy2(str(jar_file), str(jar_out))


class build_py(_build_py):
    def run(self):
        build_java()
        super().run()


class test(_test):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        _test.initialize_options(self)
        self.pytest_args = ""

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


with (Path(__file__).parent / 'README.md').open(encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='biomedicus',
    use_scm_version={
        "fallback_version": "development0",
        "write_to": "python/biomedicus/version.py"
    },
    description='A biomedical and clinical NLP engine.',
    url='https://nlpie.github.io/biomedicus',
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='~=3.5',
    author='University of Minnesota NLP/IE Group',
    author_email='nlp-ie@umn.edu',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Java',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Text Processing :: General',
        'Topic :: Text Processing :: Linguistic'
    ],
    keywords='nlp biomedical text',
    entry_points={'console_scripts': ['biomedicus=biomedicus.cli:main'], },
    package_dir={'': 'python'},
    packages=find_packages(where='python', exclude=['tests']),
    package_data={
        'biomedicus': [
            'defaultConfig.yml',
            'biomedicus-all.jar',
            'negation/negex_triggers.txt',
            'deployment/biomedicus_deploy_config.yml',
            'deployment/rtf_to_text_deploy_config.yml',
            'performance_testing/performance_multiinstance.yml',
            'performance_testing/performance_torchserve.yml',
            'performance_testing/performance_multiprocess.yml',
            'pipeline/biomedicus_default_pipeline.yml',
            'pipeline/rtf_to_text_pipeline.yml',
            'scaleout/scaleout_deploy_config.yml',
            'scaleout/scaleout_pipeline_config.yml'
        ]
    },
    install_requires=[
        'mtap>=1.0rc2',
        'numpy',
        'pyyaml',
        'regex',
        'tqdm',
        'torch',
        'stanza==1.2.0',
        'requests',
        'watchdog'
    ],
    setup_requires=[
        'pytest-runner',
        'setuptools_scm',
    ],
    tests_require=[
        'pytest'
    ],
    extras_require={
        'palliative': ['transformers[torch]', 'accelerate', 'datasets'],
        'tests': ['pytest-runner', 'pytest'],
        'docs': ['sphinx']
    },
    cmdclass={
        'test': test,
        'build_py': build_py
    }
)
