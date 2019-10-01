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

from nlpnewt import EventsClient, Pipeline, LocalProcessor, Event
from nlpnewt.io.serialization import get_serializer, SerializationProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("input-directory", metavar="INPUT_DIR")
    parser.add_argument("concepts-csv", metavar="PATH_TO_CONCEPTS_CSV")
    parser.add_argument("output-directory", metavar="OUTPUT_DIR")
    parser.add_argument("--events")

    ns = parser.parse_args(args)

    print('Reading concepts csv...')
    concepts = {}
    with open(args.concepts_csv, 'r') as f:
        for line in f.readlines():
            splits = line.split(',')
            identifier = splits[6]
            

    with EventsClient(address=ns.events) as client, Pipeline(
            LocalProcessor(SerializationProcessor(get_serializer('json'),
                                                                 output_dir=args.output_directory),
                                          component_id='serialize',
                                          client=client)
    ) as pipeline:
        for path in Path(ns.input_directory).glob('**/*.source'):
            identifier = path.stem
            with Event(event_id=identifier, client=client) as event:
                with path.open('r') as f:
                    text = f.read()




if __name__ == '__main__':
    main()
