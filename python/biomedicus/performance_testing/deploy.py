#  Copyright 2020 Regents of the University of Minnesota.
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
import shutil
import sys
import urllib.request
from argparse import ArgumentParser
from pathlib import Path
from shutil import rmtree
from subprocess import Popen, STDOUT, PIPE
from tempfile import NamedTemporaryFile
from threading import Thread
from time import sleep
from zipfile import ZipFile

import grpc
from tqdm import tqdm

from biomedicus.config import load_config


def main(args=None):
    print('Writing deployment configurations')
    parent = Path(__file__).parent
    shutil.copy(parent / 'performance_multiinstance.yml', '.')
    shutil.copy(parent / 'performance_multiprocess.yml', '.')
    shutil.copy(parent / 'performance_torchserve.yml', '.')


if __name__ == '__main__':
    main()
