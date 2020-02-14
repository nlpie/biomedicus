#  Copyright 2019 Regents of the University of Minnesota.
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

from mtap import Pipeline, Event, EventsClient, RemoteProcessor, LocalProcessor
from mtap.io.serialization import get_serializer, SerializationProcessor
from mtap.processing import ProcessingResult


class DefaultPipelineConf:
    def __init__(self):
        self.use_discovery = False
        self.events_address = '127.0.0.1:10100'
        self.sentences_id = 'biomedicus-sentences'
        self.sentences_address = '127.0.0.1:10102'
        self.tagger_id = 'biomedicus-tnt-tagger'
        self.tagger_address = '127.0.0.1:10103'
        self.acronyms_id = 'biomedicus_acronyms'
        self.acronyms_address = '127.0.0.1:10104'
        self.concepts_id = 'biomedicus-concepts'
        self.concepts_address = '127.0.0.1:10105'
        self.negation_id = 'biomedicus-negex'
        self.negation_address = '127.0.0.1:10106'
        self.include_label_text = False
        self.threads = 4

        self.serializer = None
        self.input_directory = None
        self.output_directory = None


class DefaultPipeline:
    def __init__(self, conf: DefaultPipelineConf,
                 *, events_client: EventsClient = None):
        if events_client is not None:
            self.close_client = False
            self.events_client = events_client
        elif conf.events_address is not None:
            self.close_client = True
            self.events_client = EventsClient(address=conf.events_address)
        else:
            raise ValueError("Events client or address not specified.")

        pipeline = [
            (conf.sentences_id, conf.sentences_address),
            (conf.tagger_id, conf.tagger_address),
            (conf.acronyms_id, conf.acronyms_address),
            (conf.concepts_id, conf.concepts_address),
            (conf.negation_id, conf.negation_address)
        ]
        if conf.use_discovery:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier) for identifier, _ in pipeline],
                n_threads=conf.threads
            )
        else:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier, address=addr) for identifier, addr in pipeline],
                n_threads=conf.threads
            )
        if conf.serializer is not None:
            serialization_proc = SerializationProcessor(get_serializer(conf.serializer),
                                                        conf.output_directory,
                                                        include_label_text=conf.include_label_text)
            ser_comp = LocalProcessor(serialization_proc, component_id='serializer',
                                      client=self.events_client)
            self.pipeline.append(ser_comp)

    def process_text(self, text: str, *, event_id: str = None) -> ProcessingResult:
        with Event(event_id=event_id, client=self.events_client) as event:
            document = event.create_document('plaintext', text=text)
            f = self.pipeline.run(document)
        return f

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pipeline.close()
        if self.close_client:
            self.events_client.close()


def default_pipeline_parser():
    parser = ArgumentParser(add_help=False)
    defaults = DefaultPipelineConf()
    parser.add_argument('input_directory', help="The input directory of text files to process.")
    parser.add_argument('output_directory', help="The output directory to write json out.")
    parser.add_argument('--events-address', default=defaults.events_address,
                        help="The address for the events service.")
    parser.add_argument('--sentences-address', default=defaults.sentences_address,
                        help="The address for the sentence boundary detector service.")
    parser.add_argument('--tagger-address', default=defaults.tagger_address,
                        help="The address for the pos tagger service.")
    parser.add_argument('--acronyms-address', default=defaults.acronyms_address,
                        help="The address for the acronym detector service.")
    parser.add_argument('--concepts-address', default=defaults.concepts_address,
                        help="The address for the concept detector service.")
    parser.add_argument('--negation-address', default=defaults.negation_address,
                        help="The address for the negation detection service.")
    parser.add_argument('--use_discovery', action='store_true',
                        help="If this flag is specified, all ports will be ignored and instead "
                             "service discovery will be used to connect to services.")
    parser.add_argument('--serializer', default='yml', choices=['json', 'yml', 'pickle'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")
    parser.add_argument('--threads', default=defaults.threads, type=int,
                        help="The number of threads to use for processing")
    return parser


def run_default_pipeline(conf: DefaultPipelineConf):
    _conf = DefaultPipelineConf()
    vars(_conf).update(vars(conf))
    conf = _conf
    with DefaultPipeline(conf) as default_pipeline:
        input_dir = Path(conf.input_directory)
        total = sum(1 for _ in input_dir.rglob('*.txt'))

        def source():
            for path in input_dir.rglob('*.txt'):
                with path.open('r', errors='replace') as f:
                    txt = f.read()
                relative = str(path.relative_to(input_dir))
                e = Event(event_id=relative, client=default_pipeline.events_client)
                doc = e.create_document('plaintext', txt)
                yield doc

        default_pipeline.pipeline.run_multithread(source(), total=total)
        default_pipeline.pipeline.print_times()
