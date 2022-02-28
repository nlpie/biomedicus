#  Copyright 2019 Regents of the University of Minnesota.
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
import logging
import os
from argparse import ArgumentParser
from pathlib import Path
from shutil import rmtree
from subprocess import Popen
from tempfile import NamedTemporaryFile
from typing import Optional
from zipfile import ZipFile

import requests
from mtap.deployment import Deployment
from tqdm import tqdm

from biomedicus.config import load_config

logger = logging.getLogger(__name__)

default_deployment_config = Path(__file__).parent / 'biomedicus_deploy_config.yml'


def _listen(process: Popen) -> int:
    for line in process.stdout:
        print(line.decode(), end='', flush=True)
    return process.wait()


def check_data(download=False):
    try:
        data = Path(os.environ['BIOMEDICUS_DATA'])
    except KeyError:
        data = Path.home() / '.biomedicus' / 'data'
        os.environ['BIOMEDICUS_DATA'] = str(data)

    config = load_config()
    download_url = config['data.data_url']
    data_version = config['data.version']
    version_file = data / 'VERSION.txt'
    if not data.exists():
        print('No existing data folder.')
    elif not version_file.exists():
        print('No existing version file.')
    else:
        existing_version = version_file.read_text().strip()
        if existing_version != data_version:
            print('Data folder ({}) is not most recent version ({})'.format(existing_version,
                                                                            data_version))
        else:
            logger.info('Data folder is up to date version {}'.format(data_version))
            return
    if not download:
        print(
            'It looks like you do not have the set of models distributed for BioMedICUS.\n'
            'The models are available from our website (https://nlpie.umn.edu/downloads)\n'
            'and can be installed by specifying the environment variable BIOMEDICUS_DATA\n'
            'or by placing the extracted models in ~/.biomedicus/data'
        )
        prompt = 'Would you like to download the model files to {} (Y/N)? '.format(str(data))
        download = input(prompt) in ['Y', 'y', 'Yes', 'yes']
    if download:
        download_data_to(download_url, data)
    else:
        exit()


def download_data_to(download_url, data):
    print('Starting download: ', download_url)
    if data.exists():
        rmtree(str(data))
    data.mkdir(parents=True, exist_ok=False)
    with NamedTemporaryFile() as temporary_file:
        r = requests.get(download_url, stream=True, verify=False)
        size = int(r.headers.get('content-length', -1))
        with tqdm(total=size, unit='b', unit_scale=True) as bar:
            for chunk in r.iter_content(chunk_size=1024):
                temporary_file.write(chunk)
                bar.update(1024)
        with ZipFile(temporary_file) as zf:
            print('Extracting...')
            zf.extractall(path=str(data))


def attach_biomedicus_jar(deployment: Deployment, append_to: Optional[str] = None):
    jar_path = str(Path(__file__).parent.parent / 'biomedicus-all.jar')
    classpath = deployment.shared_processor_config.java_classpath
    classpath = classpath + ':' if classpath is not None else ''
    if append_to is not None:
        classpath += append_to + ':'
    classpath += jar_path
    deployment.shared_processor_config.java_classpath = classpath


def deploy(conf):
    try:
        check_data(conf.download_data)
    except ValueError:
        return
    deployment = Deployment.from_yaml_file(conf.config)
    attach_biomedicus_jar(deployment, conf.jvm_classpath)
    if conf.rtf:
        for processor in deployment.processors:
            if processor.entry_point == 'edu.umn.biomedicus.rtf.RtfProcessor':
                processor.enabled = True
                break
    deployment.run_servers()


def download_data(_):
    try:
        check_data(True)
    except ValueError:
        return


def deployment_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        '--config',
        default=default_deployment_config,
        help='A path to a deployment configuration file to use instead of the'
             'default deployment configuration.'
    )
    parser.add_argument(
        '--jvm-classpath',
        help="A java -classpath string that will be used in addition to the biomedicus jar."
    )
    parser.add_argument(
        '--rtf', action='store_true',
        help="Enables the RTF processor."
    )
    parser.add_argument(
        '--download-data', action='store_true',
        help="If this flag is specified, automatically download the biomedicus "
             "data if it is missing."
    )
    return parser
