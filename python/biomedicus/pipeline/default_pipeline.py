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

import grpc
from mtap import Pipeline, Event, EventsClient, RemoteProcessor
from mtap.io.serialization import get_serializer


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
        self.serializer = 'json'

        self.input_directory = None
        self.output_directory = None

    def pipeline(self):
        pipeline = [
            (self.sentences_id, self.sentences_address),
            (self.tagger_id, self.tagger_address),
            (self.acronyms_id, self.acronyms_address),
            (self.concepts_id, self.concepts_address)
        ]
        if self.use_discovery:
            return Pipeline(
                *[RemoteProcessor(identifier) for identifier, _ in pipeline]
            )
        else:
            return Pipeline(
                *[RemoteProcessor(identifier, address=addr) for identifier, addr in pipeline]
            )


class DefaultPipeline:
    def __init__(self, conf: DefaultPipelineConf,
                 *, events_client: EventsClient = None):
        self.pipeline = conf.pipeline()
        if events_client is not None:
            self.close_client = False
            self.events_client = events_client
        elif conf.events_address is not None:
            self.close_client = True
            self.events_client = EventsClient(address=conf.events_address)
        else:
            raise ValueError("Events client or address not specified.")

    def process_text(self, text: str, *, event_id: str = None) -> Event:
        event = Event(event_id=event_id, client=self.events_client)
        try:
            document = event.create_document('plaintext', text=text)
            self.pipeline.run(document)
        except grpc.RpcError as e:
            print("Error processing event {}".format(event.event_id))
            event.close()
            raise e
        except (KeyboardInterrupt, InterruptedError) as e:
            event.close()
            raise e
        return event  # Hand off event to caller

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
    parser.add_argument('--use_discovery', action='store_true',
                        help="If this flag is specified, all ports will be ignored and instead "
                             "service discovery will be used to connect to services.")
    parser.add_argument('--serializer', default=defaults.serializer, choices=['json'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    return parser


def run_default_pipeline(conf: DefaultPipelineConf):
    _conf = DefaultPipelineConf()
    vars(_conf).update(vars(conf))
    conf = _conf
    default_pipeline = DefaultPipeline(conf)
    serializer = get_serializer(conf.serializer)
    for txt_file in Path(conf.input_directory).rglob('*.txt'):
        with txt_file.open() as f:
            txt = f.read()
        relative_path = str(txt_file.relative_to(conf.input_directory))
        with default_pipeline.process_text(txt, event_id=relative_path) as event:
            print('Processed document: "{}"'.format(relative_path))
            output_file = Path(conf.output_directory) / (relative_path + serializer.extension)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            serializer.event_to_file(event, output_file)

    default_pipeline.pipeline.print_times()
