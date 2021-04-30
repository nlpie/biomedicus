#  Copyright 2021 Regents of the University of Minnesota.
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
import shutil
from argparse import ArgumentParser
from pathlib import Path

from mtap.deployment import Deployment

from biomedicus.deployment.deploy_biomedicus import attach_biomedicus_jar


def deploy_rtf(conf):
    default_config = Path(__file__).parent / 'rtf_to_text_deploy_config.yml'
    if conf.write_config:
        shutil.copyfile(str(default_config), 'rtf_to_text_deploy_config.yml')
        return

    deployment_config_file = conf.config
    if deployment_config_file is None:
        deployment_config_file = default_config
    deployment = Deployment.from_yaml_file(deployment_config_file)
    attach_biomedicus_jar(deployment, conf.jvm_classpath)
    deployment.run_servers()


def rtf_deployment_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        '--config',
        help='A path to a deployment configuration file to use instead of the'
             'default deployment configuration.'
    )
    parser.add_argument(
        '--jvm-classpath',
        help="A java -classpath string that will be used in addition to the biomedicus jar."
    )
    parser.add_argument(
        '--write-config', action='store_true',
        help="Writes the default configuration file to the current directory and immediately exits."
             "Provides a base example for customization."
    )
    return parser


def add_cli_subparsers(subparsers):
    subparser = subparsers.add_parser('deploy-rtf-to-text', parents=[rtf_deployment_parser()])
    subparser.set_defaults(f=deploy_rtf)
