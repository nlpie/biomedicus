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
"""Prints the yaml metadata for all of Biomedicus's processors."""
import os
from argparse import ArgumentParser
from subprocess import call
from tempfile import NamedTemporaryFile

from biomedicus.sentences.bi_lstm import SentenceProcessor


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--output-file', default="processors.yaml")
    ns = parser.parse_args(args)

    biomedicus_jar = os.environ['BIOMEDICUS_JAR']

    from yaml import load, dump
    try:
        from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
        from yaml import Loader, Dumper

    with NamedTemporaryFile('r') as f:
        call(['java', '-cp', biomedicus_jar, 'edu.umn.nlpie.mtap.utilities.PrintProcessorMetadata',
              f.name, 'edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
              'edu.umn.biomedicus.concepts.DictionaryConceptDetector',
              'edu.umn.biomedicus.normalization.NormalizationProcessor',
              'edu.umn.biomedicus.rtf.RtfProcessor',
              'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor'])
        java_meta = load(f, Loader=Loader)

    all_meta = [x.metadata for x in [SentenceProcessor]] + java_meta
    with open(ns.output_file, 'w') as f:
        dump(all_meta, f, Dumper=Dumper)


if __name__ == '__main__':
    main()
