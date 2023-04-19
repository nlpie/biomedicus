#  Copyright 2022 Regents of the University of Minnesota.
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
"""Prints the yaml metadata for all of Biomedicus's processors."""

import os
from argparse import ArgumentParser
from tempfile import NamedTemporaryFile
from typing import Optional

from biomedicus.java_support import run_java
from biomedicus_client.cli_tools import Command


def print_processor_meta(output_file: Optional[str] = None):
    from biomedicus.dependencies.stanza_parser import StanzaParser
    from biomedicus.negation.negex import NegexProcessor
    from biomedicus.sentences.bi_lstm import SentenceProcessor
    if output_file is None:
        output_file = "processors.yaml"
    if os.path.isdir(output_file):
        output_file += "processors.yaml"
    if os.path.exists(output_file):
        raise ValueError(f"File already exists: {output_file}.")
    from yaml import load, dump
    try:
        from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
        from yaml import Loader, Dumper

    with NamedTemporaryFile('r') as f:
        return_code = run_java(
            'edu.umn.nlpie.mtap.utilities.PrintProcessorMetadata',
            f.name,
            'edu.umn.biomedicus.acronym.AcronymDetectorProcessor',
            'edu.umn.biomedicus.concepts.DictionaryConceptDetector',
            'edu.umn.biomedicus.normalization.NormalizationProcessor',
            'edu.umn.biomedicus.rtf.RtfProcessor',
            'edu.umn.biomedicus.tagging.tnt.TntPosTaggerProcessor',
            'edu.umn.biomedicus.modification.ModificationDetector',
        )
        if return_code != 0:
            raise ValueError("java metadata failed.")
        java_meta = load(f, Loader=Loader)
        java_meta = {
            m['name']: m for m in java_meta
        }

    all_meta = [
                   java_meta['biomedicus-rtf-processor']
               ] + [x.metadata for x in [SentenceProcessor, StanzaParser]] + [
                   java_meta['biomedicus-tnt-tagger'],
                   java_meta['biomedicus-acronyms'],
                   java_meta['biomedicus-normalizer'],
                   java_meta['biomedicus-concepts'],
                   java_meta['biomedicus-modification']
               ] + [x.metadata for x in [NegexProcessor]]
    with open(output_file, 'w') as f:
        dump(all_meta, f, Dumper=Dumper)


class PrintProcessorMetaCommand(Command):
    @property
    def command(self) -> str:
        return "print-processor-meta"

    @property
    def help(self) -> str:
        return "Prints metadata about available BioMedICUS processors"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('--output-file', help="Name or location to print to. Default name is 'processors.yaml'")

    def command_fn(self, conf):
        print_processor_meta(conf.output_file)
