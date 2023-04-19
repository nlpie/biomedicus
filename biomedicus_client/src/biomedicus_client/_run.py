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
"""Support for running the default pipeline by default and optionally arbitrary pipelines."""

from argparse import ArgumentParser
from typing import List

from biomedicus_client.sources import WatcherSource, rtf_source, RtfHandler, TxtHandler
from mtap import events_client
from mtap.pipeline import FilesInDirectoryProcessingSource

from biomedicus_client import default_pipeline
from biomedicus_client.cli_tools import Command


class RunCommand(Command):
    @property
    def command(self) -> str:
        return "run"

    @property
    def help(self) -> str:
        return "Runs a biomedicus pipeline."

    @property
    def parents(self) -> List[ArgumentParser]:
        return [default_pipeline.argument_parser()]

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('input_directory', help="The input directory of text files to process.")
        parser.add_argument('--extension-glob', default=None,
                            help="The extension glob used to find files to process.")
        parser.add_argument('--watch', default=False, action='store_true',
                            help="Watches the directory for new files to process.")
        parser.add_argument('--no-times', default=False, action='store_true',
                            help="Suppress printing pipeline run times after completion.")
        parser.add_argument('--log-level', default='INFO',
                            help="The log level to use.")

    def command_fn(self, conf):
        pipeline = default_pipeline.from_args(conf)
        input_directory = conf.input_directory
        with events_client(pipeline.events_address) as client:
            if conf.rtf:
                extension_glob = conf.extension_glob or "**/*.rtf"
                if conf.watch:
                    source = WatcherSource(RtfHandler(input_directory, extension_glob, client))
                else:
                    source = rtf_source(input_directory, extension_glob, client)
                params = {'document_name': 'plaintext'}
            else:
                extension_glob = conf.extension_glob or "**/*.txt"
                if conf.watch:
                    source = WatcherSource(TxtHandler(input_directory, extension_glob, client))
                else:
                    source = FilesInDirectoryProcessingSource(client,
                                                              input_directory,
                                                              extension_glob=extension_glob)
                params = None
            result = pipeline.run_multithread(source, params=params, log_level=conf.log_level)
        if not conf.no_times:
            result.print()
