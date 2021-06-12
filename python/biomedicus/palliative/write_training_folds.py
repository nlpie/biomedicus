import json
import logging
import random
from argparse import ArgumentParser
from pathlib import Path
from typing import TextIO

from mtap.io.serialization import JsonSerializer
from tqdm import tqdm

logger = logging.getLogger("biomedicus.palliative.write_training_folds")

THEME_GROUPS = [
    ('communication', ['communication']),
    ('abilities_goals_tradeoffs', ['critical_abilities', 'goals', 'tradeoffs']),
    ('decision_making', ['decision_making']),
    ('family', ['family']),
    ('fears_worries', ['fears_worries']),
    ('legal_docc', ['legal_docc']),
    ('prognosis', ['prognosis']),
    ('strength', ['strength']),
    ('understanding', ['understanding'])
]


def reduce_class(palliative_themes, n_annotators, out):
    any_theme = set()
    for theme_group, constituents in THEME_GROUPS:
        annotators_count = 0
        for annotator_name, annotators_themes in palliative_themes.annotator_themes.items():
            theme_present = False
            for theme_name in constituents:
                theme_present = annotators_themes.get(theme_name, False)
                if theme_present:
                    break
            if theme_present:
                annotators_count += 1
                any_theme.add(annotator_name)
        theme_present = annotators_count >= n_annotators / 2
        out[theme_group] = theme_present
    out["any_theme"] = len(any_theme) >= n_annotators / 2
    return out


def write_doc_examples(doc, f: TextIO):
    n_annotators = len(doc.labels['palliative_annotators'][0].annotators)
    prev_text = ''
    for annotator_themes in doc.labels['palliative_themes']:
        text = annotator_themes.text
        out = {'sentence1': prev_text, 'sentence2': text}
        out = reduce_class(annotator_themes, n_annotators, out)
        if out is not None:
            f.write(json.dumps(out))
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
        with (output_dir / '{}-validation.json'.format(i)).open('w') as f_validation, \
                (output_dir / '{}-train.json'.format(i)).open('w') as f_train:
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
