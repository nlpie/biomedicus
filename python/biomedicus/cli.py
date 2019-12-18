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


def main(args=None):
    from argparse import ArgumentParser
    from biomedicus.deployment.deploy_biomedicus import deployment_parser, deploy
    from biomedicus.pipeline.default_pipeline import default_pipeline_parser, run_default_pipeline
    parser = ArgumentParser()
    parser.set_defaults(f=lambda _: parser.print_help())
    subparsers = parser.add_subparsers()

    deployment_subparser = subparsers.add_parser('deploy', parents=[deployment_parser()],
                                                 help='Deploys the default biomedicus pipeline.')
    deployment_subparser.set_defaults(f=deploy)

    run_subparser = subparsers.add_parser('run', parents=[default_pipeline_parser()],
                                          help="Runs the default biomedicus pipeline on files "
                                               "in a directory.")
    run_subparser.set_defaults(f=run_default_pipeline)

    conf = parser.parse_args(args)
    f = conf.f
    del conf.f
    f(conf)