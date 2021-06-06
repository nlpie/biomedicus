import csv
import json
import logging
import random
from argparse import ArgumentParser
from pathlib import Path
from typing import TextIO

from mtap.io.serialization import JsonSerializer
from tqdm import tqdm

logger = logging.getLogger("biomedicus.palliative.write_training_folds")


def reduce_class(palliative_themes, n_annotators):
    is_palliative = (sum(any(themes.values())
                         for themes in palliative_themes.annotator_themes.values())
                     >= (n_annotators / 2))
    return 'theme' if is_palliative else 'no_theme'


def write_doc_examples(doc, f: TextIO):
    n_annotators = len(doc.labels['palliative_annotators'][0].annotators)
    prev_text = ''
    for annotator_themes in doc.labels['palliative_themes']:
        text = annotator_themes.text
        sentence_class = reduce_class(annotator_themes, n_annotators)
        if sentence_class is not None:
            f.write(json.dumps({'sentence1': prev_text, 'sentence2': text, 'label': sentence_class}))
            f.write('\n')
        prev_text = text


def write_examples(input_dir, output_dir, n_folds):
    deserializer = JsonSerializer
    files = list(Path(input_dir).glob('*.json'))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    random.shuffle(files)
    fold_len = len(files) // n_folds

    for i in range(n_folds):
        logger.info(f'Fold {i}')
        with (output_dir / '{}-validation.csv'.format(i)).open('w') as f_validation, \
                (output_dir / '{}-train.csv'.format(i)).open('w') as f_train:
            for j, path in enumerate(tqdm(files)):
                event = deserializer.file_to_event(path)
                if j in range(fold_len * i, fold_len * (i + 1)):
                    writer = f_validation
                else:
                    writer = f_train
                doc = event.documents['plaintext']
                write_doc_examples(doc, writer)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--n-folds', type=int, default=5)
    conf = parser.parse_args(args)
    write_examples(**vars(conf))


if __name__ == '__main__':
    main()
