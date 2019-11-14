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

from biomedicus.tokenization import detect_space_after, Token


def training_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--epochs', type=int, default=100,
                        help="number of epochs to run training.")
    parser.add_argument('--tensorboard', action='store_true', default=False,
                        help="whether to use a keras.callbacks.TensorBoard.")
    parser.add_argument('--checkpoints', type=bool, default=True,
                        help="whether to save the best model during training.")
    parser.add_argument('--early-stopping', type=bool, default=True,
                        help="whether to stop when the model stops improving.")
    parser.add_argument('--early-stopping-patience', type=int, default=5,
                        help="how many epochs without improvement before stopping.")
    parser.add_argument('--early-stopping-delta', type=float, default=0.0001,
                        help="the smallest amount loss needs to improve by to be considered "
                             "improvement by early stopping.")
    parser.add_argument('--use-class-weights', type=bool, default=True,
                        help="whether to weight the value of class loss and accuracy based on "
                             "their support.")
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help="the fraction of the data to use for validation.")
    parser.add_argument('--optimizer', default='nadam',
                        help="the keras optimizer to use. default is 'nadam'")
    parser.add_argument('--batch-size', default=32,
                        help="The batch size to use during training.")
    parser.add_argument('--sequence-length', default=32,
                        help='The sequence size to use during training.')

    parser.add_argument('--job-dir',
                        help="Path to the output directory where logs and models will be "
                             "written.")
    parser.add_argument('--input-dir', help="input directory")
    return parser



def directory_labels_generator(directory, repeat=False):
    import tensorflow as tf
    while True:
        for doc_dir, _, docs in tf.io.gfile.walk(directory):
            for doc in docs:
                if not doc.endswith('.txt'):
                    continue
                path = Path(doc_dir, doc)
                print("reading document {}".format(path))
                with tf.io.gfile.GFile(str(path), 'r') as f:
                    txt = f.read()

                labels_path = path.with_suffix('.labels')
                with tf.io.gfile.GFile(str(labels_path), 'r') as f:
                    tokens = [_split_token_line(txt, x) for x in f]
                yield doc, txt, tokens

        if not repeat:
            break


def _split_token_line(txt, line):
    """Internal method for splitting token lines from the .labels format.
    """
    if not line:
        return None

    split = line.split()

    if len(split) < 5:
        return None

    segment = int(split[0])
    begin = int(split[1])
    end = int(split[2])
    label = split[3]
    is_identifier = split[4] == '1'
    space_after = detect_space_after(txt, end)
    return Token(segment, begin, end, label, is_identifier, space_after)