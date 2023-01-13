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

import logging
from argparse import ArgumentParser
from pathlib import Path
from subprocess import Popen
from typing import List

from mtap.deployment import Deployment

from biomedicus.deployment._data_downloading import check_data
from biomedicus.java_support import attach_biomedicus_jar
from biomedicus_client.cli_tools import Command

logger = logging.getLogger(__name__)

default_deployment_config = Path(__file__).parent / 'biomedicus_deploy_config.yml'
scaleout_deploy_config = Path(__file__).parent / 'scaleout_deploy_config.yml'


def _listen(process: Popen) -> int:
    for line in process.stdout:
        print(line.decode(), end='', flush=True)
    return process.wait()


def deploy(conf):
    try:
        if not conf.offline:
            check_data(conf.download_data, with_stanza=True)
    except ValueError:
        return
    deployment = Deployment.from_yaml_file(conf.config)
    deployment.shared_processor_config.java_classpath = attach_biomedicus_jar(
        deployment.shared_processor_config.java_classpath,
        conf.jvm_classpath
    )
    if conf.rtf:
        for processor in deployment.processors:
            if processor.entry_point == 'edu.umn.biomedicus.rtf.RtfProcessor':
                processor.enabled = True
                break
    deployment.run_servers()


def deployment_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        '--config',
        default=default_deployment_config,
        help='A path to a deployment configuration file to use instead of the'
             'default deployment configuration.'
    )
    parser.add_argument(
        '--jvm-classpath',
        help="A java -classpath string that will be used in addition to the biomedicus jar."
    )
    parser.add_argument(
        '--rtf', action='store_true',
        help="Enables the RTF processor."
    )
    parser.add_argument(
        '--download-data', action='store_true',
        help="If this flag is specified, automatically download the biomedicus "
             "data if it is missing."
    )
    parser.add_argument(
        '--offline', action='store_true',
        help="Does not perform the data check before launching processors."
    )
    return parser


class DeployCommand(Command):
    @property
    def command(self) -> str:
        return "deploy"

    @property
    def help(self) -> str:
        return "Deploys a BioMedICUS pipeline."

    @property
    def parents(self) -> List[ArgumentParser]:
        return [deployment_parser()]

    def add_arguments(self, parser: ArgumentParser):
        pass  # No arguments to add

    def command_fn(self, conf):
        deploy(conf)
