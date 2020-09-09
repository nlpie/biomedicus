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
import csv
import random
from argparse import ArgumentParser
from pathlib import Path


def sample_mimic(input_file: Path, output_dir: Path, n_samples: int):
    with input_file.open(newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        next(reader)  # get rid of header line
        docs = []
        print('Reading documents from {}'.format(str(input_file)))
        for i, item in enumerate(reader, start=1):
            row_id = item[0]
            text = item[10]
            docs.append((row_id, text))
            if i % 1000 == 0:
                print('Documents read: {}'.format(i))

        print('Done reading {} documents. Sampling.'.format(i))
        docs = random.sample(docs, n_samples)

        output_dir.mkdir(parents=True, exist_ok=True)
        print('Writing documents to {}'.format(output_dir))
        for i, (row_id, text) in enumerate(docs, start=1):
            subfolder = output_dir / row_id[:1] / row_id[1:2]
            subfolder.mkdir(parents=True, exist_ok=True)
            with (subfolder / (row_id + '.txt')).open('w') as out:
                out.write(text)
                out.write('\n')
            if i % 1000 == 0:
                print('Documents written: {}'.format(i))


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_file', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('n_samples', type=int)
    conf = parser.parse_args(args)
    sample_mimic(conf.input_file, conf.output_dir, conf.n_samples)


if __name__ == '__main__':
    main()
