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

from mtap import Pipeline, LocalProcessor, Event, RemoteProcessor, events_client
from mtap.serialization import SerializationProcessor, PickleSerializer


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("input_directory", metavar="INPUT_DIR")
    parser.add_argument("concepts_csv", metavar="PATH_TO_CONCEPTS_CSV")
    parser.add_argument("output_directory", metavar="OUTPUT_DIR")
    parser.add_argument("--sentences")
    parser.add_argument("--tagger")
    parser.add_argument("--acronyms")
    parser.add_argument("--events")

    ns = parser.parse_args(args)

    print('Reading concepts csv...')
    concepts = {}
    with open(ns.concepts_csv, 'r') as f:
        for line in f.readlines():
            splits = line.split(',')
            end = splits[0]
            start = splits[1]
            cui = splits[5]
            identifier = splits[6]
            try:
                v = concepts[identifier]
            except KeyError:
                v = []
                concepts[identifier] = v
            v.append((start, end, cui))

    print('Reading mipacq source files...')
    pipeline = Pipeline(
            RemoteProcessor('biomedicus-sentences', address=ns.sentences),
            RemoteProcessor('biomedicus-tnt-tagger', address=ns.tagger),
            RemoteProcessor('biomedicus-acronyms', address=ns.acronyms),
            LocalProcessor(SerializationProcessor(PickleSerializer,
                                                  output_dir=ns.output_directory),
                           component_id='serialize'),
            events_address=ns.events
    )
    with events_client(ns.events) as events:
        for path in Path(ns.input_directory).glob('**/*.source'):
            identifier = path.stem.split('-')[0]
            try:
                doc_concepts = concepts[identifier]
            except KeyError:
                continue
            with Event(event_id=identifier, client=events) as event:
                with path.open('r') as f:
                    text = f.read()
                document = event.create_document('plaintext', text)
                with document.get_labeler('gold_concepts') as label_concept:
                    for start, end, cui in doc_concepts:
                        label_concept(start, end, cui=cui)
                pipeline.run(document)


if __name__ == '__main__':
    main()
