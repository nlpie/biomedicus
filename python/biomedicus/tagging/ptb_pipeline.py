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
from pathlib import Path

from mtap import Event, EventsClient, Document, Pipeline, RemoteProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input', metavar='INPUT_FOLDER',
                        help='A folder containing PTB formatted documents.')
    parser.add_argument('--glob', metavar='GLOB', default='*.mrg')
    parser.add_argument('--source-name', metavar='DOCUMENT_NAME', default='source',
                        help='What document to dump the PTB text into.')
    parser.add_argument('--target-name', metavar='DOCUMENT_NAME', default='plaintext',
                        help='What document to the plaintext and annotations into.')
    parser.add_argument('--events', metavar='EVENTS', default=None,
                        help='The address of the events service.')
    parser.add_argument('--ptb-reader', metavar='READER', default=None,
                        help='The address of the PTB Reader.')
    parser.add_argument('--tnt-trainer', metavar='TRAINER', default=None,
                        help='The address of the TnT trainer.')
    args = parser.parse_args(args)
    pipeline = Pipeline(
        RemoteProcessor('ptb-reader', address=args.ptb_reader,
                        params={'source_document_name': args.source_name,
                                'target_document_name': args.target_name}),
        RemoteProcessor('biomedicus-tnt-trainer', address=args.tnt_trainer,
                        params={'document_name': args.target_name}),
        events_address=args.events
    )
    with EventsClient(address=args.events) as client:
        for f in Path(args.input).rglob(args.glob):
            print('Reading:', f)
            with f.open('r') as r:
                text = r.read()
            with Event(event_id=f.name, client=client) as event:
                d = Document(args.source_name, text=text)
                event.add_document(d)
                pipeline.run(event)


if __name__ == '__main__':
    main()
