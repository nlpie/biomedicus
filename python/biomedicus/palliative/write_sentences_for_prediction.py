#  Copyright 2021 Regents of the University of Minnesota.
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
import json
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import TextIO

from mtap.io.serialization import JsonSerializer
from tqdm import tqdm

logger = logging.Logger(__name__)


def write_doc_examples(doc, f: TextIO):
    prev_text = ''
    for sentence in doc.labels['sentences']:
        text = sentence.text
        out = {
            'document': doc.event.event_id,
            'sentence_id': sentence.identifier,
            'sentence1': prev_text,
            'sentence2': text
        }
        if out is not None:
            f.write(json.dumps(out))
            f.write('\n')
        prev_text = text


def write_examples(input_dir, output_dir):
    deserializer = JsonSerializer
    files = list(Path(input_dir).glob('*.json'))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / 'predict.json').open('w') as f:
        for j, path in enumerate(tqdm(files)):
            event = deserializer.file_to_event(path)
            doc = event.documents['plaintext']
            write_doc_examples(doc, f)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('output_dir', type=Path)
    conf = parser.parse_args(args)
    write_examples(**vars(conf))


if __name__ == '__main__':
    main()
