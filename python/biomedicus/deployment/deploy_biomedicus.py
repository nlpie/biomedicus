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
import os
import signal
import urllib.request
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import Popen, STDOUT, PIPE
from threading import Event
from typing import Callable
from zipfile import ZipFile

import grpc
from tqdm import tqdm

from biomedicus.config import load_config


def listener(process: Popen) -> Callable[[], int]:
    def listen():
        for line in process.stdout:
            print(line.decode(), end='')
        return process.wait()

    return listen


def check_data(download=False):
    try:
        data = Path(os.environ['BIOMEDICUS_DATA'])
    except KeyError:
        data = Path.home() / '.biomedicus' / 'data'
        os.environ['BIOMEDICUS_DATA'] = str(data)

    if not data.exists():
        print(
            'It looks like you do not have the set of models distributed for BioMedICUS.\n'
            'The models are available from our website (https://nlpie.umn.edu/downloads)\n'
            'and can be installed by specifying the environment variable BIOMEDICUS_DATA\n'
            'or by placing the extracted models in ~/.biomedicus/data'
        )
        prompt = 'Would you like to download the model files to ~/.biomedicus/data (Y/N)? '
        if download or input(prompt) in ['Y', 'y', 'Yes', 'yes']:
            download_data_to(data)
        else:
            raise ValueError('No biomedicus data folder.')


def download_data_to(data):
    config = load_config()
    download_url = config['data.data_url']

    def report(_, read, total):
        if report.bar is None:
            report.bar = tqdm(total=total, unit='b', unit_scale=True, unit_divisor=10 ** 6)
        report.bar.update(read)

    report.bar = None
    try:
        print('Starting download: ', download_url)
        local_filename, headers = urllib.request.urlretrieve(download_url, reporthook=report)
    finally:
        report.bar.close()
    try:
        data.mkdir(parents=True, exist_ok=True)
        with ZipFile(local_filename) as zf:
            print('Extracting...')
            zf.extractall(path=str(data))
    finally:
        os.unlink(local_filename)


def deploy(conf):
    try:
        check_data(conf.download_data)
    except ValueError:
        return
    jar_path = str(Path(__file__).parent.parent / 'biomedicus-all.jar')
    calls = [
        (['python', '-m', 'biomedicus.sentences.bi_lstm', 'processor'],
         conf.sentences_port),
        (['java', '-Xms128m', '-Xmx8g', '-cp', jar_path, 'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor'],
         conf.tagger_port),
        (['java', '-Xms128m', '-Xmx8g', '-cp', jar_path, 'edu.umn.biomedicus.acronym.AcronymDetectorProcessor'],
         conf.acronyms_port),
        (['java', '-Xms128m', '-Xmx8g', '-cp', jar_path, 'edu.umn.biomedicus.concepts.DictionaryConceptDetector'],
         conf.concepts_port)
    ]
    if conf.events_address is None:
        calls.insert(0, (['python', '-m', 'mtap', 'events'], conf.events_port))
        events_address = '127.0.0.1:' + conf.events_port
    else:
        events_address = conf.events_address
    if conf.include_rtf:
        calls.append(['java', '-cp', jar_path, 'edu.umn.biomedicus.rtf.RtfProcessor',
                      '-p', conf.rtf_port, '--events', events_address])

    for i, (call, port) in enumerate(calls):
        call.extend(['-p', port])
        if events_address is None or i > 0:
            call.extend(['--events', events_address])
        if conf.discovery:
            call.append('--register')
    process_listeners = ThreadPoolExecutor(max_workers=len(calls))
    processes = []
    futures = []
    for call, _ in calls:
        p = Popen(call, stdout=PIPE, stderr=STDOUT)
        futures.append(process_listeners.submit(listener(p)))
        processes.append(p)

    def handler(_a, _b):
        print("Shutting down all processors", flush=True)
        for p in processes:
            p.send_signal(signal.SIGINT)
        for future in futures:
            future.result(timeout=5)
        e.set()

    signal.signal(signal.SIGINT, handler)

    for call, port in calls:
        with grpc.insecure_channel('127.0.0.1:' + port) as channel:
            future = grpc.channel_ready_future(channel)
            try:
                future.result(timeout=20)
            except grpc.FutureTimeoutError:
                print('Failed to launch: {}'.format(call))
                handler(None, None)

    print('Done starting all processors')
    e = Event()
    e.wait()
    print("Done shutting down all processors")


def deployment_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--config-file')
    parser.add_argument('--events-address', default=None,
                        help="An existing events service to use instead of launching one.")
    parser.add_argument('--events-port', default='10100',
                        help="The port to launch the events service on")
    parser.add_argument('--include-rtf', action='store_true',
                        help='Also launch the RTF processor.')
    parser.add_argument('--discovery', action='store_true',
                        help='Register the services with consul.')
    parser.add_argument('--rtf-port', default='10101',
                        help="The port to launch the RTF processor on.")
    parser.add_argument('--sentences-port', default='10102',
                        help="The port to launch the sentences processor on.")
    parser.add_argument('--tagger-port', default='10103',
                        help="The port to launch the tnt pos tagger on.")
    parser.add_argument('--acronyms-port', default='10104',
                        help="The port to launch the acronym detector on.")
    parser.add_argument('--concepts-port', default='10105',
                        help="The port to launch the concepts detector on.")
    parser.add_argument('--download-data', action='store_true',
                        help="If this flag is specified, automatically download the biomedicus "
                             "data if it is missing.")
    return parser
