#  Copyright 2022 Regents of the University of Minnesota.
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
"""Support for creating and running the rtf-to-text pipeline."""

from argparse import ArgumentParser, Namespace
from os import PathLike
from pathlib import Path
from typing import Union, Optional, List

from biomedicus_client.sources import rtf_source
from importlib_resources import as_file
from mtap import Pipeline, LocalProcessor, EventProcessor, processor, events_client

from biomedicus_client import pipeline_confs
from biomedicus_client.cli_tools import Command

__all__ = ['create', 'from_args', 'argument_parser', 'RunRtfToTextCommand']


@processor('write-plaintext')
class WritePlaintext(EventProcessor):
    def __init__(self, output_directory: Path):
        self.output_directory = output_directory

    def process(self, event, params):
        with (self.output_directory / (str(event.event_id) + '.txt')).open('w') as f:
            f.write(event.documents['plaintext'].text)


def create(config: Optional[Union[str, PathLike]] = None,
           *,
           events_addresses: Optional[str] = None,
           output_directory: Union[str, Path] = None,
           **_) -> Pipeline:
    """

    Args:
        config (PathLike):
        events_addresses:
        output_directory:
        **_:

    Returns:

    """
    if config is None:
        with as_file(pipeline_confs.RTF_TO_TEXT) as config:
            pipeline = Pipeline.from_yaml_file(config)
    else:
        pipeline = Pipeline.from_yaml_file(config)

    if events_addresses is not None:
        pipeline.events_address = events_addresses

    if output_directory is not None:
        pipeline += [LocalProcessor(
            WritePlaintext(Path(output_directory)),
            component_id='write_text'
        )]
    return pipeline


def argument_parser():
    """The argument parser for the biomedicus rtf-to-text pipeline.

    Returns: ArgumentParser object.

    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--config', default=None, help='Path to the pipeline configuration file.')
    parser.add_argument('--output_directory', '-o', default='output', help="The output directory to write txt out.")
    parser.add_argument('--events-addresses', default=None, help="The address for the events service.")
    return parser


def from_args(args: Namespace) -> Pipeline:
    if not isinstance(args, Namespace):
        raise ValueError('"args" parameter should be the parsed arguments from "rtf_to_text.argument_parser()"')
    return create(**vars(args))


class RunRtfToTextCommand(Command):
    @property
    def command(self) -> str:
        return "run-rtf-to-text"

    @property
    def help(self) -> str:
        return "Runs a biomedicus pipeline which converts rtf documents (Using the biomedicus rtf processor) to " \
               "plaintext documents."

    @property
    def parents(self) -> List[ArgumentParser]:
        return [argument_parser()]

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('input_directory', help="The input directory of text files to process.")
        parser.add_argument('--extension-glob', default="*.rtf",
                            help="The extension glob used to find files to process.")
        parser.add_argument('--log-level', default='INFO',
                            help="The log level for the pipeline runners.")

    def command_fn(self, conf):
        pipeline = from_args(conf)
        input_directory = Path(conf.input_directory)

        with events_client(pipeline.events_address) as client:
            source = rtf_source(input_directory, conf.extension_glob, client)
            total = sum(1 for _ in input_directory.rglob(conf.extension_glob))

            times = pipeline.run_multithread(source, total=total, log_level=conf.log_level)
        times.print()
