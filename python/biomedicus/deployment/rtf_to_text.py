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
from argparse import ArgumentParser, Namespace
from contextlib import contextmanager
from typing import Optional, List, ContextManager

from importlib_resources import files
from mtap.deployment import Deployment

from biomedicus.java_support import attach_biomedicus_jar
from biomedicus_client.cli_tools import Command

deployment_config = files('biomedicus.deployment').joinpath('rtf_to_text_deploy_config.yml')


@contextmanager
def create_deployment(config_file: Optional[str] = None,
                      jvm_classpath: Optional[str] = None,
                      log_level: Optional[str] = None,
                      **_) -> ContextManager[Deployment]:
    if config_file is None:
        config_file = deployment_config
    if log_level is None:
        log_level = 'INFO'
    deployment = Deployment.from_yaml_file(config_file)
    deployment.global_settings.log_level = log_level
    with attach_biomedicus_jar(
        deployment.shared_processor_config.java_classpath,
        jvm_classpath
    ) as java_cp:
        deployment.shared_processor_config.java_classpath = java_cp
        yield deployment


def from_args(args: Namespace) -> ContextManager[Deployment]:
    return create_deployment(**vars(args))


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        '--config',
        help='A path to a deployment configuration file to use instead of the'
             'default deployment configuration.',
        default=deployment_config
    )
    parser.add_argument(
        '--jvm-classpath',
        help="A java -classpath string that will be used in addition to the biomedicus jar."
    )
    parser.add_argument(
        '--log-level',
        help="The log level for pipeline runners."
    )
    return parser


class DeployRtfToTextCommand(Command):
    @property
    def command(self) -> str:
        return "deploy-rtf-to-text"

    @property
    def help(self) -> str:
        return "Deploys the rtf-to-text BioMedICUS pipeline."

    @property
    def parents(self) -> List[ArgumentParser]:
        return [argument_parser()]

    def add_arguments(self, parser: ArgumentParser):
        pass  # No arguments to add outside parent

    def command_fn(self, conf):
        with from_args(conf) as deployment:
            deployment.run_servers_and_wait()
