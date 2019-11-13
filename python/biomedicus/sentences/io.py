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
from pathlib import Path

from biomedicus.tokenization import detect_space_after, Token


def directory_labels_generator(directory, repeat=False, return_name=False):
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
                if return_name:
                    yield txt, doc, tokens
                else:
                    yield txt, tokens

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
