#  Copyright 2020 Regents of the University of Minnesota.
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
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Union

import math
import numpy as np
from mtap import Pipeline, Event, EventsClient, RemoteProcessor, Document
from mtap.processing import PipelineResult, ProcessingResult, ProcessingSource

SERVICES = ['events', 'sentences', 'tagger']


class PipelineConf:
    """Configuration for the biomedicus default pipeline to connect to.

    By default will connect to ``host`` and ``SERVICE_port`` of each service unless
    ``SERVICE_address`` is specified or ``use_discovery`` is ``true``.

    """
    def __init__(self):
        self.id = ""
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

        self.include_label_text = False
        self.workers = 1

        self.serializer = None
        self.input_directory = None
        self.output_directory = None

        self.limit = sys.maxsize

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
            (conf.tagger_id, conf.tagger_address)
        ]
        if conf.use_discovery:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier) for identifier, _ in pipeline]
            )
        else:
            self.pipeline = Pipeline(
                *[RemoteProcessor(identifier, address=addr) for identifier, addr in pipeline]
            )

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


def run_default_pipeline(conf: PipelineConf):
    with DefaultPipeline(conf) as default_pipeline:
        input_dir = Path(conf.input_directory)
        total = min(sum(1 for _ in input_dir.rglob('*.txt')), conf.limit)

        times = []
        chars = []

        class Source(ProcessingSource):
            def provide(self, consume: Callable[[Union[Document, Event]], None]):
                for i, path in enumerate(input_dir.rglob('*.txt'), start=1):
                    if i > conf.limit:
                        break
                    with path.open('r', errors='replace') as f:
                        txt = f.read()
                    relative = str(path.relative_to(input_dir))
                    with Event(event_id=relative, client=default_pipeline.events_client,
                               only_create_new=True) as e:
                        doc = e.create_document('plaintext', txt)
                        consume(doc)

            def receive_result(self, result: PipelineResult, event: Event):
                times.append(result.elapsed_time)
                chars.append(len(event.documents['plaintext'].text))

        start = datetime.now()
        default_pipeline.pipeline.run_multithread(Source(), total=total, n_threads=conf.workers)
        duration = datetime.now() - start
        print('Total time elapsed:', duration)
        print('Per document time:', duration / total)
        with open('{}-times-{}workers.csv'.format(conf.id, conf.workers), 'w') as f:
            f.write(default_pipeline.pipeline.pipeline_timer_stats().csv_header())
            for line in default_pipeline.pipeline.pipeline_timer_stats().timing_csv():
                f.write(line)
            for proc in default_pipeline.pipeline.processor_timer_stats():
                for line in proc.timing_csv():
                    f.write(line)
        i = list(map(lambda x: x.total_seconds(), times))
        np.save('{}-times-series-{}-workers'.format(conf.id, conf.workers), np.array(i))
        np.save('{}-chars-per-doc-{}-workers'.format(conf.id, conf.workers), np.array(chars))


def main(args=None):
    """The argument parser for the biomedicus default pipeline.

    Returns: ArgumentParser object.

    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument('input_directory', help="The input directory of text files to process.")
    parser.add_argument('--host', default='127.0.0.1',
                        help='A hostname to connect to for all services.')

    # events
    _add_address(parser, 'events', '10100')
    _add_address(parser, 'sentences', '10102', 'biomedicus-sentences')
    _add_address(parser, 'tagger', '10103', 'biomedicus-tnt-tagger')
    parser.add_argument('--id', default="", help="An identifier for output files.")
    parser.add_argument('--workers', default=1, type=int,
                        help="The number of workers to process with.")
    parser.add_argument('--limit', default=math.inf, type=int,
                        help="The number of documents (at most) to process.")
    parser.add_argument('--use-discovery', action='store_true',
                        help="If this flag is specified, all ports will be ignored and instead "
                             "service discovery will be used to connect to services.")
    parser.add_argument('--serializer', default='json', choices=['json', 'yml', 'pickle'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")

    conf = parser.parse_args(args, namespace=PipelineConf())
    run_default_pipeline(conf)


if __name__ == '__main__':
    main()
