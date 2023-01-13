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
"""Generalized command for writing out config file examples."""

import shutil
from pathlib import Path

from biomedicus_client.cli_tools.command import Command


class WriteConfigsCommand(Command):
    def __init__(self, *configs):
        self.writable_configs = {}
        for config in configs:
            self.writable_configs.update(config)

    @property
    def command(self) -> str:
        return "write-config"

    @property
    def help(self) -> str:
        return "Writes a BioMedICUS configuration file to disc so it can be edited."

    def command_fn(self, conf):
        config_file_path, output_path = conf.config, conf.path
        config_path = str(self.writable_configs[config_file_path])
        name = Path(config_path).name
        if output_path is not None:
            output_path = Path(output_path)
            if output_path.is_dir():
                output_path = str(output_path / name)
            else:
                output_path = str(output_path)
        else:
            output_path = str(Path.cwd() / name)

        print(f'Copying biomedicus configuration to "{output_path}"')
        shutil.copy2(config_path, output_path)

    def add_arguments(self, parser):
        parser.add_argument('config', choices=self.writable_configs.keys(), help="The config file to write.")
        parser.add_argument('path', metavar="PATH_TO", nargs='?',
                            help="The file name or to write the config file to.")
