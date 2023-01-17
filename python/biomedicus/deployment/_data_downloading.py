#  Copyright 2022 Regents of the University of Minnesota.
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
import pathlib
import shutil
import tempfile
import zipfile
from argparse import ArgumentParser

import requests
from tqdm import tqdm

from biomedicus.data_version import DATA_VERSION, DATA_URL
from biomedicus_client.cli_tools import Command


def check_data(download=False, with_stanza=False, noninteractive=False):
    try:
        data = pathlib.Path(os.environ['BIOMEDICUS_DATA'])
    except KeyError:
        data = pathlib.Path.home() / '.biomedicus' / 'data'
        os.environ['BIOMEDICUS_DATA'] = str(data)

    if with_stanza:
        import stanza
        stanza.download('en')

    download_url = DATA_URL
    data_version = DATA_VERSION
    version_file = data / 'VERSION.txt'
    if not data.exists():
        print('No existing data folder.')
    elif not version_file.exists():
        print('No existing version file.')
    else:
        existing_version = version_file.read_text().strip()
        if existing_version != data_version:
            print(f'Data folder at "{data}" ({existing_version}) is not expected version ({data_version})')
        else:
            print(f'Data folder at "{data}" is expected version ({data_version})')
            return
    if not download:
        if noninteractive:
            exit(1)
        print(
            'It looks like you do not have the set of models distributed for BioMedICUS.\n'
            'The models are available from (https://nlpie.github.io/downloads)\n'
            'and can be installed by specifying the environment variable BIOMEDICUS_DATA\n'
            'or by placing the extracted models in ~/.biomedicus/data'
        )
        prompt = f'Would you like to download the model files to "{data}" (Y/N)? '
        download = input(prompt) in ['Y', 'y', 'Yes', 'yes']
    if download:
        download_data_to(download_url, data)
    else:
        exit()


def download_data_to(download_url, data):
    print('Starting download: ', download_url)
    if data.exists():
        shutil.rmtree(str(data))
    data.mkdir(parents=True, exist_ok=False)
    with tempfile.NamedTemporaryFile() as temporary_file:
        r = requests.get(download_url, stream=True, verify=False)
        size = int(r.headers.get('content-length', -1))
        with tqdm(total=size, unit='b', unit_scale=True) as bar:
            for chunk in r.iter_content(chunk_size=1024):
                temporary_file.write(chunk)
                bar.update(1024)
        with zipfile.ZipFile(temporary_file) as zf:
            print('Extracting...')
            zf.extractall(path=str(data))


class DownloadDataCommand(Command):
    @property
    def command(self) -> str:
        return "download-data"

    @property
    def help(self) -> str:
        return "Checks if the BioMedICUS data is up-to-date and downloads it if not."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('--with-stanza', action='store_true', help="Also downloads stanza models.")

    def command_fn(self, conf):
        try:
            check_data(True, conf.with_stanza)
        except ValueError:
            return
