#  Copyright (c) Regents of the University of Minnesota.
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
from typing import List

from mtap.pipeline import pipeline_parser, run_pipeline_server

from biomedicus_client import default_pipeline, rtf_to_text
from biomedicus_client.cli_tools import Command


class ServePipeline(Command):
    @property
    def command(self) -> str:
        return "serve-pipeline"

    @property
    def help(self) -> str:
        return "Starts the end-to-end BioMedICUS pipeline service."

    @property
    def parents(self) -> List[ArgumentParser]:
        return [pipeline_parser()]

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            '--config',
            default=None,
            help='Path to the pipeline configuration file.'
        )
        parser.add_argument(
            '--include-label-text',
            action='store_true',
            help="Flag to include the covered text for every label"
        )
        parser.add_argument(
            '--rtf',
            action='store_true',
            help="Flag to use a source for the rtf reader instead of plain text."
        )
        parser.add_argument(
            '--rtf-address',
            help="The address (or addresses, comma separated) for the rtf to text converter processor."
        )

    def command_fn(self, conf):
        if conf.port == 0:
            conf.port = 55000
        conf.serializer = None
        pipeline = default_pipeline.from_args(conf)
        run_pipeline_server(pipeline, conf)


class ServeRtfToText(Command):
    @property
    def command(self) -> str:
        return "serve-rtf-to-text"
    
    @property
    def help(self) -> str:
        return "Starts the RTF to text BioMedICUS pipeline service."
    
    @property
    def parents(self) -> List[ArgumentParser]:
        return [pipeline_parser()]
    
    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            '--config',
            default=None,
            help='Path to the pipeline configuration file.'
        )

    def command_fn(self, conf):
        if conf.port == 0:
            conf.port = 55001
        conf.serializer = None
        pipeline = rtf_to_text.from_args(conf)
        run_pipeline_server(pipeline, conf)
