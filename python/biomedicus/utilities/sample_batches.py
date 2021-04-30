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
import argparse
import pathlib
import random
import shutil


def sample_into_batches(input_directory: pathlib.Path,
                        output_directory: pathlib.Path,
                        batch_size: int = 100,
                        extension_glob: str = '*.txt',
                        test_only: bool = False):
    files = list(input_directory.glob(extension_glob))
    random.shuffle(files)
    for i in range(0, len(files), batch_size):
        batch_no = i // batch_size + 1
        batch_dir = output_directory / f'{batch_no :03d}'
        if not test_only:
            batch_dir.mkdir(parents=True, exist_ok=True)
        for j, file in enumerate(files[i:i+batch_size]):
            relative = file.relative_to(input_directory)
            cp_path = batch_dir / (f'{batch_no:03d}_{(j + 1):03d}_' + relative.name)
            if test_only:
                print(f'cp {file} {cp_path}')
            else:
                shutil.copy(file, cp_path)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('input_directory', type=pathlib.Path)
    parser.add_argument('output_directory', type=pathlib.Path)
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--extension-glob', default='*.txt')
    parser.add_argument('--test-only', action='store_true')
    conf = parser.parse_args(args)
    sample_into_batches(**vars(conf))


if __name__ == '__main__':
    main()
