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
from argparse import ArgumentParser
from importlib.resources import files
from typing import Optional

from mtap.deployment import Deployment

from biomedicus.java_support import attach_biomedicus_jar
from biomedicus_client.cli_tools import Command

default_rtf_to_text_deployment_config = files('biomedicus.deployment').joinpath('rtf_to_text_deploy_config.yml')


def create_rtf_to_text_deployment(config_file: Optional[str] = None, jvm_classpath: Optional[str] = None) -> Deployment:
    if config_file is None:
        config_file = default_rtf_to_text_deployment_config
    deployment = Deployment.from_yaml_file(config_file)
    deployment.shared_processor_config.java_classpath = attach_biomedicus_jar(
        deployment.shared_processor_config.java_classpath,
        jvm_classpath
    )
    return deployment


class DeployRtfToTextCommand(Command):
    @property
    def command(self) -> str:
        return "deploy-rtf-to-text"

    @property
    def help(self) -> str:
        return "Deploys the rtf-to-text BioMedICUS pipeline."

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            '--config',
            help='A path to a deployment configuration file to use instead of the'
                 'default deployment configuration.',
            default=default_rtf_to_text_deployment_config
        )
        parser.add_argument(
            '--jvm-classpath',
            help="A java -classpath string that will be used in addition to the biomedicus jar."
        )

    def command_fn(self, conf):
        deployment = create_rtf_to_text_deployment(conf.config, conf.jvm_classpath)
        deployment.run_servers()
