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
from argparse import Namespace

import pytest
from mtap import Document, GenericLabel

from biomedicus.deployment import check_data
# BiLSTM import required for pickle
from biomedicus.sentences import bi_lstm


@pytest.fixture(name='bi_lstm_model')
def fixture_bi_lstm_model():
    check_data()
    conf = Namespace(
        chars_file=None,
        hparams_file=None,
        model_file=None,
        words_file=None,
        torch_device='cpu',
        download_data=False,
        embeddings=None,
        mp=False
    )
    proc = bi_lstm.create_processor(conf)
    yield proc
    proc.close()


@pytest.mark.integration
def test_sentences_unknown_character(bi_lstm_model):
    document = Document('plaintext', text='• Sentence which contains unknown character.')
    bi_lstm_model.process_document(document, {})
    assert document.labels['sentences'] == [GenericLabel(2, 44)]
