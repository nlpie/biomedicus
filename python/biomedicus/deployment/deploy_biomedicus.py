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
from argparse import ArgumentParser
from subprocess import Popen
from concurrent.futures import ThreadPoolExecutor


def listener(process: Popen):
    def listen():
        while process.poll() is None:
            process


def deploy(conf):
    events_address = '127.0.0.1:' + conf.events_port
    calls = [
        ['python', '-m', 'biomedicus.sentences.bi_lstm', 'processor', '-p', conf.sentences_port,
         '--events', events_address],
        ['java', '']
    ]
    process_listeners = ThreadPoolExecutor(max_workers=1 + len(calls))



def deployment_parser():
    parser = ArgumentParser()
    parser.add_argument('--config-file')
    parser.add_argument('--events-port', default='10100')
    parser.add_argument('--include-rtf', action='store_true')
    parser.add_argument('--rtf-port', default='10101')
    parser.add_argument('--sentences-port', default='10102')
    parser.add_argument('--tagger-port', default='10103')
    parser.add_argument('--acronyms-port', default='10104')
    parser.add_argument('--concepts-port', default='10105')
    return parser
