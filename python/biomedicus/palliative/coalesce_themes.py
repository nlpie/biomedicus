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
from typing import Dict, Any, Optional

from mtap import DocumentProcessor, processor

THEMES = ('communication', 'critical_abilities', 'decision_making', 'family',
          'fears_worries', 'goals', 'legal_docc', 'prognosis', 'strength', 'tradeoffs',
          'understanding')


@processor('coalesce-palliative-themes')
class CoalescePalliativeThemesProcessor(DocumentProcessor):
    def process_document(self, document, params):
        annotators = document.labels['palliative_annotators'][0].annotators
        themes_idx = document.labels['annotator_themes']
        with document.get_labeler('palliative_themes', ) as PalliativeThemes:
            for sentence in document.labels['sentences']:
                themes = {annotator_name: set() for annotator_name in annotators}
                for overlapping_theme in themes_idx.overlapping(sentence):
                    annotator_name = overlapping_theme.annotator_name
                    annotator_themes = themes[annotator_name]
                    for theme_name in THEMES:
                        if getattr(overlapping_theme, theme_name, False):
                            annotator_themes.add(theme_name)

                PalliativeThemes(
                    sentence.start_index,
                    sentence.end_index,
                    annotator_themes={
                        annotator_name: {theme_name: (theme_name in themes[annotator_name])
                                         for theme_name in THEMES}
                        for annotator_name in annotators
                    }
                )
