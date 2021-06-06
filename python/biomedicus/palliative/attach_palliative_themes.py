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
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from mtap import DocumentProcessor, processor


@processor('attach-palliative-themes')
class AttachPalliativeThemesProcessor(DocumentProcessor):
    """Attaches the annotated palliative themes from the UIMA CAS JSON serialized files.

    """
    def __init__(self, input_directory):
        super().__init__()
        self.input_directory = Path(input_directory)

    def process_document(self, document, params):
        name = document.event.event_id
        annotators = set()
        with document.get_labeler('annotator_themes') as AnnotatorTheme:
            for zipfile in (self.input_directory / name).glob('*.zip'):
                with TemporaryDirectory() as tempdir:
                    shutil.unpack_archive(zipfile, extract_dir=tempdir, format='zip')
                    for annotator_json in Path(tempdir).glob("*.json"):
                        annotator_name = annotator_json.stem
                        annotators.add(annotator_name)
                        with annotator_json.open('r') as f:
                            cas_json = json.load(f)
                        try:
                            themes = cas_json['_views']['_InitialView']['Theme']
                            for theme in themes:
                                AnnotatorTheme(
                                    theme['begin'], theme['end'],
                                    annotator_name=annotator_name,
                                    communication=theme['Communication'],
                                    critical_abilities=theme['Critical_Abilities'],
                                    decision_making=theme['Decision_Making'],
                                    family=theme['Family'],
                                    fears_worries=theme['Fears_Worries'],
                                    goals=theme['Goals'],
                                    legal_docc=theme['Legal_Docc'],
                                    prognosis=theme['Prognosis'],
                                    strength=theme['Strength'],
                                    tradeoffs=theme['Tradeoffs'],
                                    understanding=theme['Understanding']
                                )
                        except KeyError:
                            pass
        with document.get_labeler('palliative_annotators') as PalliativeAnnotators:
            PalliativeAnnotators(0, 0, annotators=list(annotators))
