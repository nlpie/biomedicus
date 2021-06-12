#  Copyright 2021 Regents of the University of Minnesota.
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
from argparse import ArgumentParser
from pathlib import Path

from mtap import Pipeline, RemoteProcessor, LocalProcessor, Event
from mtap.io.serialization import SerializationProcessor, JsonSerializer


def run_sentences_pipeline(input_directory, skip_file, output_directory):
    skip_documents = set(Path(skip_file).open('r').read().splitlines())
    events_address = 'localhost:50100'
    with Pipeline(
            RemoteProcessor('biomedicus-sentences', address='localhost:50300'),
            LocalProcessor(
                SerializationProcessor(JsonSerializer, output_directory)
            ),
            events_address=events_address
    ) as pipeline:
        total = sum(1 for _ in input_directory.rglob('*.txt'))

        def source():
            for path in input_directory.rglob('*.txt'):
                relative = str(path.relative_to(input_directory))
                if relative not in skip_documents:
                    with path.open('r') as f:
                        txt = f.read()
                    with Event(event_id=relative, client=pipeline.events_client,
                               only_create_new=True) as e:
                        doc = e.create_document('plaintext', txt)
                        yield doc

        pipeline.run_multithread(source(), total=total, workers=8)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_directory', type=Path)
    parser.add_argument('skip_file', type=Path)
    parser.add_argument('output_directory', type=Path)
    conf = parser.parse_args(args)
    run_sentences_pipeline(conf.input_directory, conf.skip_file, conf.output_directory)


if __name__ == '__main__':
    main()
