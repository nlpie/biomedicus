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
import sys
from argparse import ArgumentParser

from mtap import Pipeline, RemoteProcessor, Event, events_client


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--events', default='localhost:50100')
    parser.add_argument('--sentences', default='localhost:50300')
    conf = parser.parse_args(args)
    pipeline = Pipeline(
        RemoteProcessor('biomedicus-sentences', address=conf.sentences),
        events_address=conf.events
    )
    with events_client(conf.events) as events:
        text = sys.stdin.read()
        with Event(client=events) as event:
            doc = event.create_document('plaintext', text)
            result = pipeline.run(doc)
            for sentence in doc.labels['sentences']:
                print('S: "', sentence.text, '"')
            for k, v in result[0].timing_info.items():
                print('{}: {}'.format(k, v))


if __name__ == '__main__':
    main()
