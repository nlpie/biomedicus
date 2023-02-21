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
from contextlib import contextmanager
from typing import List, Optional, ContextManager

from importlib_resources import files
from mtap.deployment import Deployment

from biomedicus.deployment._data_downloading import check_data
from biomedicus.java_support import attach_biomedicus_jar
from biomedicus_client.cli_tools import Command

logger = logging.getLogger(__name__)

deployment_config = files('biomedicus.deployment').joinpath('biomedicus_deploy_config.yml')
scaleout_deploy_config = files('biomedicus.deployment').joinpath('scaleout_deploy_config.yml')


@contextmanager
def create_deployment(offline: bool = False,
                      download_data: bool = False,
                      noninteractive: bool = False,
                      config: Optional[str] = None,
                      log_level: Optional[str] = None,
                      jvm_classpath: Optional[str] = None,
                      rtf: bool = False,
                      host: Optional[str] = None,
                      **_) -> ContextManager[Deployment]:
    config = config if config is not None else deployment_config
    log_level = log_level if log_level is not None else 'INFO'
    if not offline:
        check_data(download_data, with_stanza=True, noninteractive=noninteractive)
    deployment = Deployment.from_yaml_file(config)
    if host is not None:
        deployment.global_settings.host = host
    deployment.global_settings.log_level = log_level
    with attach_biomedicus_jar(
        deployment.shared_processor_config.java_classpath,
        jvm_classpath
    ) as java_cp:
        deployment.shared_processor_config.java_classpath = java_cp
        if rtf:
            for processor in deployment.processors:
                if processor.entry_point == 'edu.umn.biomedicus.rtf.RtfProcessor':
                    processor.enabled = True
                    break
        yield deployment


def from_args(args) -> ContextManager[Deployment]:
    return create_deployment(**vars(args))


def argument_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        '--config',
        default=deployment_config,
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
        '--noninteractive', action='store_true',
        help="If this flag is specified the process will exit with a non-zero exit code if"
             "the data is not provided or an incorrect version instead of querying the terminal."
    )
    parser.add_argument(
        '--offline', action='store_true',
        help="Does not perform the data check before launching processors."
    )
    parser.add_argument(
        '--log-level', default='INFO',
        help="The log level for all processors."
    )
    parser.add_argument(
        '--host', default='127.0.0.1',
        help="The hostname/ip to deploy the services on."
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
        return [argument_parser()]

    def add_arguments(self, parser: ArgumentParser):
        pass  # No arguments to add

    def command_fn(self, conf):
        with from_args(conf) as deployment:
            deployment.run_servers_and_wait()
