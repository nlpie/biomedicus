import logging
from typing import Dict, Any, Optional

import nlpnewt
from nlpnewt.events import Document
from nlpnewt.processing import DocumentProcessor

from biomedicus.sentences.models.base import SentenceModel

LOGGER = logging.getLogger(__name__)


@nlpnewt.processor('biomedicus-sentences')
class SentenceProcessor(DocumentProcessor):
    def __init__(self, model: SentenceModel):
        LOGGER.info("Initializing sentence processor.")
        self.model = model

    def process(self, document: Document, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text = document.text
        sentences = self.model.predict_txt(self.model, )
