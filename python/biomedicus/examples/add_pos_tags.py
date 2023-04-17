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

from mtap import Pipeline, RemoteProcessor, LocalProcessor, events_client
from mtap.serialization import get_serializer, SerializationProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("input_directory", metavar="INPUT_DIR")
    parser.add_argument("output_directory", metavar="OUTPUT_DIR")
    parser.add_argument("--events")
    parser.add_argument("--sentences")
    parser.add_argument("--tagger")
    args = parser.parse_args(args)

    json_serializer = get_serializer('json')

    input_dir = Path(args.input_directory)
    pipeline = Pipeline(
        RemoteProcessor('biomedicus-sentences', address=args.sentences),
        RemoteProcessor('biomedicus-tnt-tagger', address=args.tagger),
        LocalProcessor(SerializationProcessor(get_serializer('json'),
                                              output_dir=args.output_directory),
                       component_id='serialize'),
        events_address=args.events
    )
    times = pipeline.create_times()
    with events_client(args.events) as client:
        for path in input_dir.glob("**/*.json"):
            print("READING FILE:", str(path))
            with json_serializer.file_to_event(path, client=client) as event:
                document = event['plaintext']
                result = pipeline.run(document)
                times.add_result_times(result)

    times.print()


if __name__ == '__main__':
    main()
