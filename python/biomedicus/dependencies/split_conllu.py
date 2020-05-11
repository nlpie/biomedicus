#  Copyright 2020 Regents of the University of Minnesota.
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
import random
import re
from argparse import ArgumentParser
from math import floor
from pathlib import Path

boundary = re.compile(r'(?:\n)\n')


def split(input_file: Path, train_ratio: float):
    with input_file.open('r') as io:
        txt = io.read()
    prev = 0
    examples = []
    for match in boundary.finditer(txt):
        end = match.start()
        example = txt[prev:end]
        if not example.isspace():
            examples.append(example)
        prev = match.end()

    total = len(examples)
    train = floor(train_ratio * total)
    random.shuffle(examples)
    with open('train.conllu', 'w') as out:
        for example in examples[:train]:
            out.write(example)
            out.write('\n\n')
    with open('test.conllu', 'w') as out:
        for example in examples[train:]:
            out.write(example)
            out.write('\n\n')


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_file', type=Path)
    parser.add_argument('--train-ratio', type=float, default=0.8)
    conf = parser.parse_args(args)
    split(**vars(conf))


if __name__ == '__main__':
    main()
