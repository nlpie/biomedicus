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
"""Creation of ArgumentParser from Command classes."""

from biomedicus_client.cli_tools import Command


def create_parser(*subcommands: Command):
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.set_defaults(f=lambda _: parser.print_help())
    parser.add_argument('--log-level', default='INFO')
    subparsers = parser.add_subparsers()

    for command in subcommands:
        command.add_subparser(subparsers)

    return parser
