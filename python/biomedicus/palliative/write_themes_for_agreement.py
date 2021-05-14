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
import csv
from argparse import ArgumentParser
from pathlib import Path

from mtap.io.serialization import JsonSerializer
from tqdm import tqdm

from biomedicus.palliative.coalesce_themes import THEMES


def annotator_class(annotator_themes, theme_name, annotator):
    try:
        annotator_result = annotator_themes.annotator_themes[annotator][theme_name]
        return 1 if annotator_result else 0
    except KeyError:
        return 0


def process_for_agreement(input_dir, output_dir, annotators_file):
    annotators = Path(annotators_file).read_text().splitlines()
    deserializer = JsonSerializer
    files = list(Path(input_dir).glob('*.json'))
    files.sort()
    for theme in THEMES:
        print('Doing ' + theme)
        with (Path(output_dir) / theme).with_suffix('.csv').open('w') as out:
            writer = csv.writer(out)
            writer.writerow(['sent_id'] + annotators)
            for f in tqdm(files):
                file_id = f.stem
                e = deserializer.file_to_event(f)
                doc = e.documents['plaintext']
                for annotator_themes in doc.labels['palliative_themes']:
                    sent_id = str(file_id) + ':' + str(annotator_themes.identifier)
                    line = (sent_id,) + tuple(annotator_class(annotator_themes, theme, annotator)
                                              for annotator in annotators)
                    writer.writerow(line)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('annotators_file', type=Path)
    conf = parser.parse_args(args)
    process_for_agreement(**vars(conf))


if __name__ == '__main__':
    main()
