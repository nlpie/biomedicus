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
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import Popen, STDOUT, PIPE
from threading import Event
from typing import Callable


def listener(process: Popen) -> Callable[[], int]:
    def listen():
        for line in process.stdout:
            print(line.decode(), end='')
        return process.wait()
    return listen


def check_data():
    try:
        data = Path(os.environ['data'])
    except KeyError:
        data = Path.home() / '.biomedicus' / 'data'

    if not data.exists():




def deploy(conf):
    check_data()
    events_address = '127.0.0.1:' + conf.events_port
    jar_path = str(Path(__file__).parent.parent / 'biomedicus-all.jar')
    calls = [
        ['python', '-m', 'mtap', 'events', '-p', conf.events_port],
        ['python', '-m', 'biomedicus.sentences.bi_lstm', 'processor',
         '-p', conf.sentences_port, '--events', events_address],
        ['java', '-cp', jar_path, 'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor',
         '-p', conf.tagger_port, '--events', events_address],
        ['java', '-cp', jar_path, 'edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
         '-p', conf.acronyms_port, '--events', events_address],
        ['java', '-cp', jar_path, 'edu.umn.biomedicus.concepts.DictionaryConceptDetector',
         '-p', conf.concepts_port, '--events', events_address],
    ]
    if conf.include_rtf:
        calls.append(['java', '-cp', jar_path, 'edu.umn.biomedicus.rtf.RtfProcessor',
                      '-p', conf.rtf_port, '--events', events_address])
    process_listeners = ThreadPoolExecutor(max_workers=len(calls))
    processes = []
    futures = []
    for call in calls:
        p = Popen(call, stdout=PIPE, stderr=STDOUT)
        processes.append(p)
        futures.append(process_listeners.submit(listener(p)))

    e = Event()

    def handler(_a, _b):
        print("Shutting down all processors", flush=True)
        for p in processes:
            p.send_signal(signal.SIGINT)
        for future in futures:
            future.result(timeout=5)
        e.set()

    signal.signal(signal.SIGINT, handler)
    e.wait()
    print("Done shutting down all processors")


def deployment_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--config-file')
    parser.add_argument('--events-port', default='10100')
    parser.add_argument('--include-rtf', action='store_true')
    parser.add_argument('--rtf-port', default='10101')
    parser.add_argument('--sentences-port', default='10102')
    parser.add_argument('--tagger-port', default='10103')
    parser.add_argument('--acronyms-port', default='10104')
    parser.add_argument('--concepts-port', default='10105')
    return parser
