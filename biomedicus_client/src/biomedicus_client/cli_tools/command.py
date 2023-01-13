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
"""Abstract class for a cli command."""

from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import List


class Command(ABC):
    @property
    @abstractmethod
    def command(self) -> str:
        raise NotImplementedError()

    @property
    def parents(self) -> List[ArgumentParser]:
        return []

    @property
    @abstractmethod
    def help(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def add_arguments(self, parser: ArgumentParser):
        raise NotImplementedError()

    @abstractmethod
    def command_fn(self, conf):
        raise NotImplementedError()

    def add_subparser(self, subparsers):
        subparser = subparsers.add_parser(self.command, parents=self.parents)
        self.add_arguments(subparser)

        def fn(conf):
            self.command_fn(conf)

        subparser.set_defaults(f=fn)
