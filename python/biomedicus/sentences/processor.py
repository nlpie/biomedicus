from argparse import Namespace

import logging
from typing import Dict, Any, Optional, List

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
        batch_size = params.get('batch_size', 32)
        text = document.text
        sentences = self.model.predict_txt(text, batch_size, include_tokens=False)
