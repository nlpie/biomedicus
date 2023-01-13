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

import os
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
from typing import Optional

from biomedicus_client.cli_tools import Command


class ProcessListener(Thread):
    def __init__(self, p: Popen, **kwargs):
        super().__init__(**kwargs)
        self.p = p
        self.return_code = None

    def run(self):
        for line in self.p.stdout:
            print(line.decode(), end='')
        self.return_code = self.p.wait()


def get_java():
    try:
        java_home = os.environ['JAVA_HOME']
    except KeyError:
        return 'java'
    return os.path.join(java_home, 'bin', 'java')


def attach_biomedicus_jar(*jar_strings: Optional[str]) -> str:
    jar_path = str(Path(__file__).parent / 'biomedicus-all.jar')
    all_jars = [jar_path]
    for jar_string in jar_strings:
        if jar_string is not None:
            jars = jar_string.split(':')
            all_jars.extend(jars)
    return ':'.join(all_jars)


def create_call(*args, cp=None):
    return [get_java(), '-cp', attach_biomedicus_jar(cp)] + list(args)


def run_java(*args, cp=None):
    p = Popen(create_call(cp=cp, *args), stdout=PIPE, stderr=STDOUT)
    listener = ProcessListener(p)
    listener.start()
    try:
        listener.join()
    except KeyboardInterrupt:
        pass


class RunJavaCommand(Command):
    @property
    def command(self) -> str:
        return "java "

    @property
    def help(self) -> str:
        return "Calls java with the BioMedICUS jar on the classpath."

    def command_fn(self, conf):
        run_java(cp=conf.cp, *conf.args)

    def add_arguments(self, parser):
        parser.add_argument('cp', help="The classpath option for Java.")
        parser.add_argument('args', nargs='+', help="Any additional args passed to the java executable.")
