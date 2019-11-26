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
import os
import sys
from argparse import ArgumentParser

from mtap import events, EventsClient, Pipeline, RemoteProcessor, Event


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('events_service', default='localhost:8500')
    parser.add_argument('sentences_service', default='localhost:8501')
    conf = parser.parse_args(args)
    with Pipeline(
        RemoteProcessor('biomedicus-sentences', address=conf.sentences_service)
    ) as pipeline, EventsClient(address=conf.events_service) as events_client:
        text = sys.stdin.read()
        with Event(client=events_client) as event:
            doc = event.create_document('plaintext', text)
            pipeline.run(doc)
            for sentence in doc.get_label_index('sentences'):
                print('S: "', sentence.text, '"')


if __name__ == '__main__':
    main()
