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

from nlpnewt import EventsClient, Event, Pipeline, RemoteProcessor, LocalProcessor
from nlpnewt.io.serialization import get_serializer, SerializationProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("input_directory", metavar="INPUT_DIR")
    parser.add_argument("output_directory", metavar="OUTPUT_DIR")
    args = parser.parse_args(args)

    input_dir = Path(args.input_directory)
    with EventsClient() as client, Pipeline(
        RemoteProcessor('biomedicus-rtf-processor', params={'binary_data_name': 'rtf',
                                                            'output_document_name': 'plaintext'}),
        RemoteProcessor('biomedicus-sentences', params={'document_name': 'plaintext'}),
        LocalProcessor(SerializationProcessor(get_serializer('json'),
                                              output_dir=args.output_directory),
                       component_id='serialize',
                       client=client)
    ) as pipeline:
        for path in input_dir.glob("*.rtf"):
            with path.open('rb') as f:
                contents = f.read()
            with Event(event_id=path.stem, client=client) as event:
                event.binaries['rtf'] = contents
                pipeline.run(event)


if __name__ == '__main__':
    main()
