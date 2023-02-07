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
"""The biomedicus command line interface."""

import logging

from biomedicus.deployment import (
    default_deployment,
    DownloadDataCommand,
    rtf_to_text
)
from biomedicus.java_support import RunJavaCommand
from biomedicus.utilities.print_all_processors_metadata import PrintProcessorMetaCommand
from biomedicus_client import cli_tools
from biomedicus_client.cli_tools import WriteConfigsCommand

SERVER_CONFIGS = {
    'deploy': default_deployment.deployment_config,
    'scaleout_deploy': default_deployment.scaleout_deploy_config,
    'rtf_to_text': rtf_to_text.deployment_config
}


def main(args=None):
    parser = cli_tools.create_parser(
        WriteConfigsCommand(SERVER_CONFIGS),
        default_deployment.DeployCommand(),
        RunJavaCommand(),
        DownloadDataCommand(),
        PrintProcessorMetaCommand(),
        rtf_to_text.DeployRtfToTextCommand(),
    )

    conf = parser.parse_args(args)
    logging.basicConfig(level=conf.log_level)
    f = conf.f
    f(conf)
