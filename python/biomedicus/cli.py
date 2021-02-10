#  Copyright 2019 Regents of the University of Minnesota.
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
import os
import shutil
from pathlib import Path
from subprocess import STDOUT, PIPE, Popen
from threading import Thread

from biomedicus.pipeline.default_pipeline import run_write_pipeline_config


class ProcessListener(Thread):
    def __init__(self, p: Popen, **kwargs):
        super().__init__(**kwargs)
        self.p = p
        self.return_code = None

    def run(self):
        for line in self.p.stdout:
            print(line.decode(), end='')
        self.return_code = self.p.wait()


def run_java(conf):
    jar_path = str(Path(__file__).parent / 'biomedicus-all.jar')
    cp = os.environ.get('CLASSPATH', None)
    if cp is not None:
        cp = cp + ':' + jar_path
    else:
        cp = jar_path
    call_args = ['java', '-cp', cp] + conf.args
    p = Popen(call_args, stdout=PIPE, stderr=STDOUT)
    listener = ProcessListener(p)
    listener.start()
    try:
        listener.join()
    except KeyboardInterrupt:
        pass


def write_config(conf):
    config_path = str(Path(__file__).parent / 'defaultConfig.yml')
    if conf.path is not None:
        output_path = str(Path(conf.path) / 'biomedicusConfig.yml')
    else:
        output_path = str(Path.cwd() / 'biomedicusConfig.yml')

    print('Copying biomedicus configuration to "{}"'.format(output_path))
    shutil.copy2(config_path, output_path)


def main(args=None):
    from argparse import ArgumentParser
    from biomedicus.deployment.deploy_biomedicus import deployment_parser, deploy
    from biomedicus.pipeline.default_pipeline import default_pipeline_parser, run_default_pipeline
    parser = ArgumentParser()
    parser.set_defaults(f=lambda _: parser.print_help())
    parser.add_argument('--log-level', default='INFO')
    subparsers = parser.add_subparsers()

    deployment_subparser = subparsers.add_parser('deploy', parents=[deployment_parser()],
                                                 help='Deploys the default biomedicus pipeline.')
    deployment_subparser.set_defaults(f=deploy)

    run_subparser = subparsers.add_parser('run', parents=[default_pipeline_parser()],
                                          help="Runs the default biomedicus pipeline on files "
                                               "in a directory.")
    run_subparser.set_defaults(f=run_default_pipeline)

    run_java_subparser = subparsers.add_parser('java',
                                               help="Calls Java with the biomedicus jar on "
                                                    "the classpath.")
    run_java_subparser.add_argument('args', nargs='+')
    run_java_subparser.set_defaults(f=run_java)

    write_config_subparser = subparsers.add_parser('write-config',
                                                   help="Writes the default biomedicus "
                                                        "configuration to disc so it can be "
                                                        "edited.")
    write_config_subparser.add_argument('path', metavar="PATH_TO", nargs='?',
                                        help="The location to write the config file to.")
    write_config_subparser.set_defaults(f=write_config)

    write_pipeline_subparser = subparsers.add_parser('write-pipeline',
                                                     help="Writes the default biomedicus pipeline"
                                                          "to the current working directory.")
    write_pipeline_subparser.set_defaults(f=run_write_pipeline_config)

    conf = parser.parse_args(args)
    logging.basicConfig(level=conf.log_level)
    f = conf.f
    f(conf)
