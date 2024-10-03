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
"""The biomedicus command line interface."""

import logging

from biomedicus.deployment import (
    DownloadDataCommand,
    confs as deployment_confs,
    default_deployment,
    rtf_to_text
)
from biomedicus.java_support import RunJavaCommand
from biomedicus.pipeline_service import ServePipeline, ServeRtfToText
from biomedicus.utilities.print_all_processors_metadata import PrintProcessorMetaCommand
from biomedicus_client import cli_tools
from biomedicus_client.cli_tools import WriteConfigsCommand

__all__ = ('main',)


SERVER_CONFIGS = {
    'deploy': deployment_confs.DEFAULT,
    'scaleout_deploy': deployment_confs.SCALEOUT,
    'rtf_to_text': deployment_confs.RTF_TO_TEXT
}


def main(args=None):
    parser = cli_tools.create_parser(
        WriteConfigsCommand(SERVER_CONFIGS),
        default_deployment.DeployCommand(),
        RunJavaCommand(),
        DownloadDataCommand(),
        PrintProcessorMetaCommand(),
        rtf_to_text.DeployRtfToTextCommand(),
        ServePipeline(),
        ServeRtfToText()
    )

    conf = parser.parse_args(args)
    logging.basicConfig(level=conf.log_level)
    f = conf.f
    f(conf)
