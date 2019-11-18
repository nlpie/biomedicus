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
import re
from argparse import ArgumentParser
from pathlib import Path

period_apostrophe = re.compile(r"[.'’]")
other_punct_symbols = re.compile(r'[^#\w]+')
digit = re.compile(r'\d')


def preprocess_pubmed(text):
    text = text.lower()
    text = other_punct_symbols.sub(' ', text)
    text = digit.sub('#', text)
    return text


def merge_and_preprocess_pubmed(input_directory, output_file):
    with Path(output_file).open('w') as out_f:
        for path in Path(input_directory).glob('**/*.txt'):
            if path.is_dir():
                continue
            with path.open('r', errors='replace') as in_f:
                text = in_f.read()
                out_f.write(preprocess_pubmed(text))


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_directory')
    parser.add_argument('output_file')
    config = parser.parse_args(args)
    merge_and_preprocess_pubmed(config.input_directory, config.output_file)


if __name__ == '__main__':
    main()
