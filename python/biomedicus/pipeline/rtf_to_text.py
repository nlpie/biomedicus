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
import os
import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

from mtap import Pipeline, EventsClient, LocalProcessor, EventProcessor, processor

from biomedicus.pipeline.sources import rtf_source


@processor('write-plaintext')
class WritePlaintext(EventProcessor):
    def __init__(self, output_directory: Path):
        self.output_directory = output_directory

    def process(self, event, params):
        with (self.output_directory / (str(event.event_id) + '.txt')).open('w') as f:
            f.write(event.documents['plaintext'].text)


def rtf_to_text_pipeline_parser():
    """The argument parser for the biomedicus default pipeline.

    Returns: ArgumentParser object.

    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument('input_directory', help="The input directory of text files to process.")
    parser.add_argument('output_directory', help="The output directory to write json out.")
    parser.add_argument('--config', default=None,
                        help='Path to the pipeline configuration file.')
    parser.add_argument('--events', default='localhost:50100',
                        help="The address for the events service.")
    parser.add_argument('--extension-glob', default='*.rtf',
                        help="The extension glob used to find files to process.")
    parser.add_argument('--serializer', default='json', choices=['json', 'yml', 'pickle', 'None'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")
    parser.add_argument('--workers', type=int,
                        help="The number of workers (documents being processed in parallel) "
                             "to use for processing. By default will use the cpu count divided"
                             "by 2.")
    parser.add_argument('--max-failures', type=int, default=0,
                        help="The maximum number of errors before quitting.")
    parser.add_argument('--write-config', action='store_true',
                        help="Writes the configuration for the pipeline and exits.")
    return parser


def run_rtf_to_text_pipeline(config: Namespace):
    default_config = str(Path(__file__).parent / 'rtf_to_text_pipeline.yml')
    if config.write_config:
        print('Copying from "{}" to "{}"'.format(default_config, str(Path.cwd() / 'rtf_to_text_pipeline.yml')))
        shutil.copy2(default_config, 'rtf_to_text_pipeline.yml')
        return

    config_file = config.config
    if config_file is None:
        config_file = default_config

    workers = config.workers
    if workers is None:
        workers = max(os.cpu_count() // 2, 1)

    with Pipeline.from_yaml_file(config_file) as pipeline:
        pipeline += [LocalProcessor(
            WritePlaintext(Path(config.output_directory)),
            component_id='write_text'
        )]

        input_directory = Path(config.input_directory)

        source = rtf_source(input_directory, config.extension_glob,
                            pipeline.events_client)
        total = sum(1 for _ in input_directory.rglob(config.extension_glob))

        pipeline.run_multithread(source, workers=workers, total=total, max_failures=config.max_failures)
        pipeline.print_times()


def add_cli_subparsers(subparsers):
    subparser = subparsers.add_parser('run-rtf-to-text', parents=[rtf_to_text_pipeline_parser()])
    subparser.set_defaults(f=run_rtf_to_text_pipeline)
