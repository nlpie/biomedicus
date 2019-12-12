# Copyright 2019 Regents of the University of Minnesota.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import re
from argparse import ArgumentParser

date_identifier = re.compile(r'\[\*\*\s*(\d\d?\d?\d?[-/]\d\d?[-/]\d\d?\d?\d?|\d\d?[-/]\d\d?)\s*\*\*\]')
telephone = re.compile(r'\[\*\*.*telephone.*\*\*\]')
name = re.compile(r'\[\*\*.*name.*\*\*\]')
identifier = re.compile(r'\[\*\*.*\*\*\]')
period_apostrophe = re.compile(r"[.'’]")
other_punct_symbols = re.compile(r'[^#\w]+')
digit = re.compile(r'\d')


def preprocess_mimic(text):
    text = text.lower()
    text = date_identifier.sub('\1', text)
    text = name.sub('NAME', text)
    text = telephone.sub('###-###-###', text)
    text = identifier.sub('IDENTIFIER', text)
    text = other_punct_symbols.sub(' ', text)
    text = digit.sub('#', text)
    return text


def dump_mimic(input_file, output_file):
    with open(input_file, newline='') as csvfile, open(output_file, 'w') as out:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # get rid of header line
        for line in reader:
            text = preprocess_mimic(line[10])
            out.write(text)
            out.write('\n')


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    config = parser.parse_args(args)
    dump_mimic(config.input_file, config.output_file)


if __name__ == '__main__':
    main()
