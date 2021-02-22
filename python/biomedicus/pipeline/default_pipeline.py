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
import multiprocessing
import os
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional, Union

from mtap import Pipeline, Event, EventsClient, LocalProcessor
from mtap.io.serialization import get_serializer, SerializationProcessor
from mtap.processing import ProcessingResult, FilesInDirectoryProcessingSource


class DefaultPipeline:
    """The biomedicus default pipeline for processing clinical documents.

    Attributes
        events_client (mtap.EventsClient): An MTAP events client used by the pipeline.
        pipeline (mtap.Pipeline): An MTAP pipeline to use to process documents.

    """
    def __init__(self, conf_path: Union[str, Path],
                 output_directory: Union[str, Path],
                 *, events_address: Optional[str] = None,
                 events_client: EventsClient = None,
                 serializer: Optional[str] = None,
                 include_label_text: bool = False):
        if events_address == 'None' or events_address == 'none' or events_address == 'null' or events_address == '':
            events_address = None
        if events_client is not None:
            self.close_client = False
            self.events_client = events_client
        else:
            self.close_client = True
            self.events_client = EventsClient(address=events_address)

        self.pipeline = Pipeline.from_yaml_file(conf_path)

        if serializer == 'None':
            serializer = None
        if serializer is not None:
            serialization_proc = SerializationProcessor(get_serializer(serializer),
                                                        output_directory,
                                                        include_label_text=include_label_text)
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
    default_config = str(Path(__file__).parent / 'biomedicus_default_pipeline.yml')
    parser.add_argument('--config', default=default_config,
                        help='Path to the pipeline configuration file.')
    parser.add_argument('--events', default='localhost:10100',
                        help="The address for the events service.")
    parser.add_argument('--extension-glob', default='*.txt',
                        help="The extension glob used to find files to process.")
    parser.add_argument('--serializer', default='json', choices=['json', 'yml', 'pickle', 'None'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")
    parser.add_argument('--threads', type=int,
                        help="The number of threads (documents being processed in parallel) "
                             "to use for processing. By default will use the cpu count divided"
                             "by 2.")
    return parser


def run_default_pipeline(config: Namespace):
    threads = config.threads
    if threads is None:
        threads = max(os.cpu_count() // 2, 1)

    with DefaultPipeline(conf_path=config.config,
                         output_directory=config.output_directory,
                         events_address=config.events,
                         serializer=config.serializer,
                         include_label_text=config.include_label_text) as default_pipeline:
        source = FilesInDirectoryProcessingSource(default_pipeline.events_client,
                                                  config.input_directory,
                                                  extension_glob=config.extension_glob)
        default_pipeline.pipeline.run_multithread(source, n_threads=threads)
        default_pipeline.pipeline.print_times()


def run_write_pipeline_config(_: Namespace):
    from_path = str(Path(__file__).parent / 'biomedicus_default_pipeline.yml')
    print('Copying from "{}" to "{}"'.format(from_path, str(Path.cwd() / 'biomedicus_default_pipeline.yml')))
    shutil.copy2(from_path, 'biomedicus_default_pipeline.yml')
