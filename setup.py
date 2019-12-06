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
"""A biomedical and clinical NLP engine developed by the University of
Minnesota NLP/IE Group."""

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as _test


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


setup(
    name='biomedicus',
    use_scm_version={
        "fallback_version": "development0",
        "write_to": "python/biomedicus/version.py"
    },
    description='A biomedical and clinical NLP engine.',
    python_requires='~=3.5',
    author='University of Minnesota NLP/IE Group',
    author_email='nlp-ie@umn.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Text Processing :: General',
        'Topic :: Text Processing :: Linguistic'
    ],
    keywords='nlp biomedical text',
    package_dir={'': 'python'},
    packages=find_packages(where='python', exclude=['tests']),
    package_data={
        'biomedicus': ['defaultConfig.yml']
    },
    install_requires=[
        'mtap',
        'numpy',
        'pyyaml',
        'regex'
    ],
    setup_requires=[
        'pytest-runner',
        'setuptools_scm',
    ],
    tests_require=[
        'pytest'
    ],
    extras_require={
        'torch': 'torch',
        'torch-gpu': 'torch-gpu',
        'tests': ['pytest-runner', 'pytest'],
        'docs': ['sphinx']
    },
    cmdclass={
        'test': test,
    }
)
