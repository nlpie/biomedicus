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

from mtap import EventsClient, Event, Pipeline, RemoteProcessor, LocalProcessor
from mtap.io.serialization import JsonSerializer, SerializationProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("input_directory", metavar="INPUT_DIR")
    parser.add_argument("output_directory", metavar="OUTPUT_DIR")
    parser.add_argument("--events")
    parser.add_argument("--rtf")
    parser.add_argument("--tagger")
    parser.add_argument("--acronyms")
    parser.add_argument("--sentences")
    args = parser.parse_args(args)

    input_dir = Path(args.input_directory)
    with EventsClient(address=args.events) as client, Pipeline(
            RemoteProcessor('rtf-processor', address=args.rtf,
                            params={'binary_data_name': 'rtf',
                                    'output_document_name': 'plaintext'}),
            RemoteProcessor('sentences', address=args.sentences,
                            params={'document_name': 'plaintext'}),
            RemoteProcessor('tnt-tagger', address=args.tagger,
                            params={'document_name': 'plaintext'}),
            RemoteProcessor('acronyms', address=args.acronyms),
            LocalProcessor(SerializationProcessor(JsonSerializer,
                                                  output_dir=args.output_directory),
                           component_id='serialize',
                           client=client)
    ) as pipeline:
        for path in input_dir.glob("**/*.rtf"):
            with path.open('rb') as f:
                contents = f.read()
            with Event(event_id=path.stem, client=client) as event:
                event.binaries['rtf'] = contents
                pipeline.run(event)

        pipeline.print_times()


if __name__ == '__main__':
    main()
