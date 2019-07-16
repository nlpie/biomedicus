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
import logging
from typing import Dict, Any

from nlpnewt.events import Document
from nlpnewt.processing import DocumentProcessor
from nlpnewt.processing.descriptions import label_index, parameter, processor

from biomedicus.sentences.models import SentenceModel, InputMapper

logger = logging.getLogger(__name__)


@processor('biomedicus-sentences',
           description="Labels sentences given document text.",
           entry_point=__name__,
           parameters=[
               parameter('batch_size', data_type='int',
                         description='The batch size, number of sets of 32 tokens that are '
                                     'processed at once.',
                         required=False)
           ],
           outputs=[
               label_index('sentences')
           ])
class SentenceProcessor(DocumentProcessor):
    def __init__(self, model: SentenceModel, input_mapper: InputMapper):
        logger.info("Initializing sentence processor.")
        self.model = model
        self.input_mapper = input_mapper

    def process_document(self, document: Document,
                         params: Dict[str, Any]):
        batch_size = params.get('batch_size', 32)
        text = document.text
        sentences = self.model.predict_txt(text, batch_size, self.input_mapper,
                                           include_tokens=False)
        with document.get_labeler('sentences', distinct=True) as labeler:
            for sentence in sentences:
                labeler(sentence.start_index, sentence.end_index)
