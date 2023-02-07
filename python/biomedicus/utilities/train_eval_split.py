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
from argparse import ArgumentParser
from pathlib import Path
from shutil import copy2

import numpy as np


def sample_and_move(input_dir: Path,
                    output_dir: Path,
                    glob: str,
                    eval_ratio: float,
                    only_name: bool = False):
    all_files = [f for f in input_dir.rglob(glob)]
    np.random.shuffle(all_files)
    cutoff = len(all_files) * eval_ratio
    eval_folder = output_dir / 'eval'
    eval_folder.mkdir(parents=True, exist_ok=True)
    train_folder = output_dir / 'train'
    train_folder.mkdir(parents=True, exist_ok=True)
    for i, file in enumerate(all_files):
        dest = eval_folder if i < cutoff else train_folder
        to = dest / (file.name if only_name else file.relative_to(input_dir))
        to.parent.mkdir(parents=True, exist_ok=True)
        copy2(str(file), str(to))


def main(args=None):
    parser = ArgumentParser(description='Splits files into a training and evaluation set.')
    parser.add_argument('--eval-ratio', default=.2, type=float,
                        help='What ratio of files should be taken as evaluation.')
    parser.add_argument('--glob', default='**/*.txt', metavar='GLOB',
                        help='Which matching files should be randomly sampled and copied.')
    parser.add_argument('--only-name', action='store_true',
                        help='Whether to put the files directly in the destination folders. '
                             'By default will maintain the relative path from the input directory.')
    parser.add_argument('input_dir', metavar='INPUT_DIR', type=Path,
                        help='The input directory.')
    parser.add_argument('output_dir', metavar='OUTPUT_DIR', type=Path,
                        help='The output directory. Subdirectories named "eval" and "train" will '
                             'be made in this directory.')
    args = parser.parse_args(args)
    sample_and_move(**vars(args))


if __name__ == '__main__':
    main()
