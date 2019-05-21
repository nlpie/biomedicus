import logging
from typing import Dict, Any, Optional

import nlpnewt
import yaml
from nlpnewt.events import Document
from nlpnewt.processing import DocumentProcessor, ProcessorContext

from biomedicus.config import load_config
from biomedicus.sentences.vocabulary import Vocabulary

LOGGER = logging.getLogger(__name__)


@nlpnewt.processor('biomedicus-sentences')
class SentenceProcessor(DocumentProcessor):
    def __init__(self, context: ProcessorContext):
        LOGGER.info("Initializing sentence processor.")
        self.context = context
        config = load_config()
        vocabulary = Vocabulary(config['sentences.vocab_dir'], config['sentences.word_embeddings'])

        options = {}
        with open(config['sentences.hparams_file'], 'r') as config_file:
            options.update(yaml.load(config_file))

    def process(self, document: Document, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass