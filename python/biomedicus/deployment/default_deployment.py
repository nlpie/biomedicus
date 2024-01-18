from argparse import ArgumentParser
from contextlib import contextmanager
from typing import List, Optional, ContextManager

from importlib_resources import as_file
from mtap.deployment import Deployment

from biomedicus.deployment import confs
from biomedicus.deployment._data_downloading import check_data
from biomedicus.java_support import attach_biomedicus_jar
from biomedicus_client.cli_tools import Command


@contextmanager
def create_deployment(config: Optional[str] = None,
                      offline: bool = False,
                      download_data: bool = False,
                      noninteractive: bool = False,
                      log_level: Optional[str] = None,
                      jvm_classpath: Optional[str] = None,
                      rtf: bool = False,
                      host: Optional[str] = None,
                      startup_timeout: Optional[float] = None,
                      **_) -> ContextManager[Deployment]:
    if not offline:
        check_data(download_data, noninteractive=noninteractive)

    if config is None:
        with as_file(confs.DEFAULT) as config:
            deployment = Deployment.from_yaml_file(config)
    else:
        deployment = Deployment.from_yaml_file(config)

    if host is not None:
        deployment.global_settings.host = host

    log_level = log_level if log_level is not None else 'INFO'
    deployment.global_settings.log_level = log_level

    startup_timeout = startup_timeout or 30
    deployment.shared_processor_config.startup_timeout = startup_timeout

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
        '--host', default=None,
        help="The hostname/ip to deploy the services on."
    )
    parser.add_argument(
        '--startup-timeout', type=float,
        help="The timeout (in seconds) for individual processor services to deploy before failure."
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
