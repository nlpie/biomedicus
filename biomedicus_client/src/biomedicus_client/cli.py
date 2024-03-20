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
"""biomedicus_client command line interface"""

import logging

from biomedicus_client import pipeline_confs
from biomedicus_client._run import RunCommand
from biomedicus_client.cli_tools import create_parser, WriteConfigsCommand
from biomedicus_client.rtf_to_text import RunRtfToTextCommand

__all__ = ('main',)


CLIENT_CONFIGS = {
    'pipeline': pipeline_confs.DEFAULT,
    'scaleout_pipeline': pipeline_confs.SCALEOUT,
    'rtf_only_pipeline': pipeline_confs.RTF_TO_TEXT
}


def main(args=None):
    parser = create_parser(
        WriteConfigsCommand(CLIENT_CONFIGS),
        RunCommand(),
        RunRtfToTextCommand()
    )
    conf = parser.parse_args(args)
    logging.basicConfig(level=conf.log_level)
    f = conf.f
    try:
        f(conf)
    except KeyboardInterrupt:
        exit(-1)
