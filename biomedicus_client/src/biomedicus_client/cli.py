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
"""biomedicus_client command line interface"""

import logging

from biomedicus_client.cli_tools import create_parser, WriteConfigsCommand
from biomedicus_client.pipeline import RunCommand, default_pipeline, rtf_to_text

CLIENT_CONFIGS = {
    'pipeline': default_pipeline.default_pipeline_config,
    'run': default_pipeline.default_pipeline_config,
    'scaleout-pipeline': default_pipeline.scaleout_pipeline_config,
    'rtf-to-text-pipeline': rtf_to_text.default_rtf_to_text_pipeline_config
}


def main(args=None):
    parser = create_parser(
        WriteConfigsCommand(CLIENT_CONFIGS),
        RunCommand(),
        rtf_to_text.RunRtfToTextCommand()
    )
    conf = parser.parse_args(args)
    logging.basicConfig(level=conf.log_level)
    f = conf.f
    f(conf)
