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
from argparse import ArgumentParser

import sys
from mtap import EventsClient, Pipeline, RemoteProcessor, Event


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--events-service', default='localhost:10100')
    parser.add_argument('--sentences-service', default='localhost:10102')
    conf = parser.parse_args(args)
    with Pipeline(
        RemoteProcessor('biomedicus-sentences', address=conf.sentences_service)
    ) as pipeline, EventsClient(address=conf.events_service) as events_client:
        text = sys.stdin.read()
        with Event(client=events_client) as event:
            doc = event.create_document('plaintext', text)
            result = pipeline.run(doc)
            for sentence in doc.get_label_index('sentences'):
                print('S: "', sentence.text, '"')
            for k, v in result[0].timing_info.items():
                print('{}: {}'.format(k, v))


if __name__ == '__main__':
    main()
