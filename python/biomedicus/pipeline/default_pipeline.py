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
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

from mtap import Pipeline, Event, EventsClient, RemoteProcessor, LocalProcessor
from mtap.io.serialization import get_serializer, SerializationProcessor
from mtap.processing import ProcessingResult

SERVICES = ['events', 'sentences', 'tagger', 'acronyms', 'concepts', 'negation',
            'selective_dependencies', 'deepen', 'section_headers']


class PipelineConf:
    """Configuration for the biomedicus default pipeline to connect to.

    By default will connect to ``host`` and ``SERVICE_port`` of each service unless
    ``SERVICE_address`` is specified or ``use_discovery`` is ``true``.

    """
    def __init__(self):
        self.use_discovery = False
        self.host = '127.0.0.1'

        self.events_port = '10100'
        self.events_address = None

        self.sentences_port = '10102'
        self.sentences_address = None
        self.sentences_id = 'biomedicus-sentences'

        self.tagger_port = '10103'
        self.tagger_address = None
        self.tagger_id = 'biomedicus-tnt-tagger'

        self.acronyms_port = '10104'
        self.acronyms_address = None
        self.acronyms_id = 'biomedicus-acronyms'

        self.concepts_port = '10105'
        self.concepts_address = None
        self.concepts_id = 'biomedicus-concepts'

        self.negation_port = '10106'
        self.negation_address = None
        self.negation_id = 'biomedicus-negex-triggers'

        self.selective_dependencies_port = '10107'
        self.selective_dependencies_address = None
        self.selective_dependencies_id = 'biomedicus-selective-dependencies'

        self.deepen_port = '10108'
        self.deepen_address = None
        self.deepen_id = 'biomedicus-deepen'

        self.section_headers_port = '10109'
        self.section_headers_address = None
        self.section_headers_id = 'biomedicus-section-headers'

        self.include_label_text = False
        self.threads = 4

        self.serializer = None
        self.input_directory = None
        self.output_directory = None

    def populate_addresses(self):
        for service in SERVICES:
            if getattr(self, service + '_address') is None:
                setattr(self, service + '_address',
                        self.host + ':' + getattr(self, service + '_port'))


class DefaultPipeline:
    """The biomedicus default pipeline for processing clinical documents.

    Attributes
        events_client (mtap.EventsClient): An MTAP events client used by the pipeline.
        pipeline (mtap.Pipeline): An MTAP pipeline to use to process documents.

    """
    def __init__(self, conf: PipelineConf, *, events_client: EventsClient = None):
        conf.populate_addresses()
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
            (conf.section_headers_id, conf.section_headers_address),
            (conf.tagger_id, conf.tagger_address),
            (conf.acronyms_id, conf.acronyms_address),
            (conf.concepts_id, conf.concepts_address),
            (conf.negation_id, conf.negation_address),
            (conf.selective_dependencies_id, conf.selective_dependencies_address),
            (conf.deepen_id, conf.deepen_address)
        ]
        if conf.use_discovery:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier) for identifier, _ in pipeline]
            )
        else:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier, address=addr) for identifier, addr in pipeline]
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


def _add_address(parser: ArgumentParser, service: str, default_port: str,
                 service_id: Optional[str] = None):
    mutex = parser.add_mutually_exclusive_group()
    mutex.add_argument('--' + service + '-port', default=default_port,
                       help='The port for the ' + service + ' service to use in conjunction with '
                                                            'the default host.')
    mutex.add_argument('--' + service + '-address', default=None,
                       help='A full address (host and port) to use instead of the default host '
                            'and --' + service + '-port.')
    if service_id is not None:
        parser.add_argument('--' + service + '-id', default=service_id,
                            help='A service ID to use instead of the default service ID.')


def default_pipeline_parser():
    """The argument parser for the biomedicus default pipeline.

    Returns: ArgumentParser object.

    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument('input_directory', help="The input directory of text files to process.")
    parser.add_argument('output_directory', help="The output directory to write json out.")
    parser.add_argument('--host', default='127.0.0.1',
                        help='A hostname to connect to for all services.')

    # events
    _add_address(parser, 'events', '10100')
    _add_address(parser, 'sentences', '10102', 'biomedicus-sentences')
    _add_address(parser, 'tagger', '10103', 'biomedicus-tnt-tagger')
    _add_address(parser, 'acronyms', '10104', 'biomedicus-acronyms')
    _add_address(parser, 'concepts', '10105', 'biomedicus-concepts')
    _add_address(parser, 'negation', '10106', 'biomedicus-negex-triggers')
    _add_address(parser, 'selective-dependencies', '10107', 'biomedicus-selective-dependencies')
    _add_address(parser, 'deepen', '10108', 'biomedicus-deepen')
    _add_address(parser, 'section-headers', '10109', 'biomedicus-section-headers')

    parser.add_argument('--use_discovery', action='store_true',
                        help="If this flag is specified, all ports will be ignored and instead "
                             "service discovery will be used to connect to services.")
    parser.add_argument('--serializer', default='json', choices=['json', 'yml', 'pickle'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")
    parser.add_argument('--threads', default=4, type=int,
                        help="The number of threads (documents being processed in parallel) "
                             "to use for processing")
    return parser


def run_default_pipeline(config: Namespace):
    conf = PipelineConf()
    vars(conf).update(vars(config))

    with DefaultPipeline(conf) as default_pipeline:
        input_dir = Path(conf.input_directory)
        total = sum(1 for _ in input_dir.rglob('*.txt'))

        def source():
            for path in input_dir.rglob('*.txt'):
                with path.open('r', errors='replace') as f:
                    txt = f.read()
                relative = str(path.relative_to(input_dir))
                with Event(event_id=relative, client=default_pipeline.events_client,
                           only_create_new=True) as e:
                    doc = e.create_document('plaintext', txt)
                    yield doc

        default_pipeline.pipeline.run_multithread(source(), total=total, n_threads=conf.threads)
        default_pipeline.pipeline.print_times()
