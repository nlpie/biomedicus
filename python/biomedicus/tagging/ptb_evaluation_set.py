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

from mtap import Event, Document, Pipeline, RemoteProcessor, LocalProcessor
from mtap.serialization import SerializationProcessor, PickleSerializer


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input', metavar='INPUT_DIR',
                        help='A folder containing PTB formatted documents.')
    parser.add_argument('output', metavar='OUTPUT_DIR',
                        help='A folder to write the json files to.')
    parser.add_argument('--glob', metavar='GLOB', default='*.mrg')
    parser.add_argument('--events', metavar='EVENTS', default=None,
                        help='The address of the events service.')
    parser.add_argument('--ptb-reader', metavar='READER', default=None,
                        help='The address of the PTB Reader.')
    args = parser.parse_args(args)
    with Pipeline(
            RemoteProcessor('ptb-reader', address=args.ptb_reader,
                            params={'source_document_name': 'source',
                                    'target_document_name': 'gold',
                                    'pos_tags_index': 'gold_tags'}),
            LocalProcessor(SerializationProcessor(PickleSerializer, output_dir=args.output),
                           component_id='serializer'),
            events_address=args.events
    ) as pipeline:
        for f in Path(args.input).rglob(args.glob):
            print('Reading:', f)
            with f.open('r') as r:
                text = r.read()
            with Event(event_id=f.name, client=pipeline.events_client) as event:
                d = Document('source', text=text)
                event.add_document(d)
                pipeline.run(event)


if __name__ == '__main__':
    main()
