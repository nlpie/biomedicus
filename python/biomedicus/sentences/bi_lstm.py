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
import re
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import numpy as np
import torch
import yaml
from mtap import processor_parser, Document, processor, run_processor
from mtap.processing import DocumentProcessor
from mtap.processing.descriptions import label_index
from time import time
from torch import nn, optim
from torch.nn import functional as F
from torch.nn.utils.rnn import pad_packed_sequence, pack_padded_sequence, \
    PackedSequence

from biomedicus.config import load_config
from biomedicus.sentences.input import InputMapping
from biomedicus.sentences.vocabulary import load_char_mapping
from biomedicus.utilities.embeddings import load_vectors

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader as Loader, Dumper as Dumper

logger = logging.getLogger(__name__)


class CharCNN(nn.Module):
    def __init__(self, conf, characters):
        super().__init__()

        self.character_embeddings = nn.Embedding(characters, conf.dim_char, padding_idx=0)
        self.dropout = nn.Dropout(p=conf.dropout)
        self.char_conv = nn.Conv1d(conf.dim_char, conf.char_cnn_output_channels,
                                   conf.char_cnn_kernel_size)

    def forward(self, words):
        embeddings = self.character_embeddings(words)
        embeddings = self.dropout(embeddings)
        # swap to (word, channels, characters)
        embedding_channels = embeddings.permute(0, 2, 1)
        char_channels = self.char_conv(embedding_channels)
        pools = F.max_pool1d(char_channels, char_channels.shape[-1])
        return pools


def f1_precision_recall(tp, fp, fn):
    if tp + fn == 0:
        return 0., 0., 0.
    tp = tp.float()
    fp = fp.float()
    fn = fn.float()
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    if precision + recall == 0.:
        f1 = 0.
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return f1, precision, recall


class BiLSTM(nn.Module):
    def __init__(self, conf, characters, pretrained):
        super().__init__()

        self.char_cnn = CharCNN(conf, characters)

        pretrained = torch.tensor(pretrained, dtype=torch.float32)
        self.word_embeddings = nn.Embedding.from_pretrained(pretrained, padding_idx=0)

        concatted_word_rep_features = pretrained.shape[1] + conf.char_cnn_output_channels
        self.lstm = nn.LSTM(concatted_word_rep_features,
                            conf.lstm_hidden_size, num_layers=2,
                            dropout=conf.dropout,
                            bidirectional=True, batch_first=True)
        self.batch_norm = nn.BatchNorm1d(concatted_word_rep_features)

        # projection from hidden to the "begin of sentence" score
        self.hidden2bos = nn.Linear(2 * conf.lstm_hidden_size, 1)
        self.hparams = vars(conf)
        self.dropout = nn.Dropout(p=conf.dropout)

    def forward(self, chars, words, sequence_lengths):
        assert chars.shape[0] == words.shape[0]
        assert chars.shape[1] == words.shape[1]
        # flatten the batch and sequence dims into words (batch * sequence, word_len, 1)
        word_chars = pack_padded_sequence(chars, sequence_lengths, batch_first=True,
                                          enforce_sorted=False)
        # run the char_cnn on it and then reshape back to [batch, sequence, ...]
        char_pools = PackedSequence(self.char_cnn(word_chars.data), word_chars.batch_sizes,
                                    word_chars.sorted_indices, word_chars.unsorted_indices)
        char_pools, _ = pad_packed_sequence(char_pools, batch_first=True)
        char_pools = torch.squeeze(char_pools, -1)

        # Look up the word embeddings
        embeddings = self.word_embeddings(words)
        embeddings = self.dropout(embeddings)

        # Create word representations from the concatenation of the char-cnn derived representation
        # and the word embedding representation
        word_reps = torch.cat((char_pools, embeddings), -1)

        # bath normalization, batch-normalize all words
        word_reps = word_reps.view(-1, word_reps.shape[-1])
        word_reps = self.batch_norm(word_reps)
        word_reps = word_reps.view(embeddings.shape[0], embeddings.shape[1], -1)
        word_reps = self.dropout(word_reps)

        # Run LSTM on the sequences of word representations to create contextual word
        # representations
        packed_word_reps = pack_padded_sequence(word_reps, sequence_lengths,
                                                batch_first=True,
                                                enforce_sorted=False)
        packed_contextual_word_reps, _ = self.lstm(packed_word_reps)
        contextual_word_reps, _ = pad_packed_sequence(packed_contextual_word_reps, batch_first=True)
        # Project to the "begin of sentence" space for each word
        contextual_word_reps = self.dropout(contextual_word_reps)
        return self.hidden2bos(contextual_word_reps)

    def predict(self, char_ids, word_ids):
        with torch.no_grad():
            logits = self(char_ids, word_ids, torch.tensor([len(char_ids[0])]))
            predictions = torch.round(torch.sigmoid(logits))
            return predictions


def train_on_data(model: BiLSTM, conf, train, validation, pos_weight):
    model_name = "{}".format(time())

    with (Path(conf.job_dir) / (model_name + '.hparyml')).open('w') as f:
        yaml.dump(model.hparams, f)

    optimizer = optim.Adam(model.parameters())
    old_f1 = 0.

    pos_weight = torch.tensor(pos_weight)
    step = 0
    average_loss = 0

    last_report = datetime.min

    print('STARTING TRAINING')
    for epoch in range(conf.epochs):
        total_tp = torch.tensor(0, dtype=torch.int64)
        total_fn = torch.tensor(0, dtype=torch.int64)
        total_fp = torch.tensor(0, dtype=torch.int64)

        for i, ((char_ids, word_ids), labels, lengths) in enumerate(train.batches()):
            model.train(True)
            step += 1
            model.zero_grad()

            logits = model(char_ids, word_ids, lengths)

            maxlen = labels.shape[1]
            mask = torch.arange(maxlen).view(1, -1) < lengths.view(-1, 1)
            mask = mask.view(-1)

            loss_fn = torch.nn.BCEWithLogitsLoss(weight=mask, pos_weight=pos_weight)
            flat_logits = logits.view(-1)
            flat_labels = labels.view(-1).float()
            loss = loss_fn(flat_logits, flat_labels)

            l1_regularization = 0.01 * torch.norm(torch.cat([x.view(-1) for x in model.hidden2bos.parameters()]))
            loss += l1_regularization

            loss.backward()
            optimizer.step()

            flat_predictions = torch.round(torch.sigmoid(flat_logits))
            true = flat_labels == 1
            tp = torch.sum(flat_predictions[true * mask] == 1., dtype=torch.int64)
            fn = torch.sum(flat_predictions[true * mask] == 0., dtype=torch.int64)
            fp = torch.sum(flat_predictions[(~true) * mask] == 1., dtype=torch.int64)
            total_tp += tp
            total_fn += fn
            total_fp += fp

            now = datetime.now()
            if (now - last_report).total_seconds() > 1:
                last_report = now
                f1, precision, recall = f1_precision_recall(total_tp, total_fp, total_fn)

                average_loss = (loss + (step - 1) * average_loss) / step

                print(
                    '\rEpoch [{}]:  {}/{} loss: {:.3f} - precision: {:.3%} - recall: {:.3%} - f1: {:.3%}'
                    .format(epoch + 1, i, train.n_batches, average_loss, precision, recall, f1))

        with torch.no_grad():
            model.train(False)
            val_tp = torch.tensor(0, dtype=torch.int64)
            val_fn = torch.tensor(0, dtype=torch.int64)
            val_fp = torch.tensor(0, dtype=torch.int64)
            for (char_ids, word_ids), labels, lengths in validation.batches():
                logits = model(char_ids, word_ids, lengths)

                maxlen = labels.shape[1]
                mask = torch.arange(maxlen)[None, :] < lengths[:, None]
                mask = mask.view(-1)

                flat_logits = logits.view(-1)
                flat_labels = labels.view(-1)
                flat_predictions = torch.round(torch.sigmoid(flat_logits))

                true = flat_labels == 1
                tp = torch.sum(flat_predictions[true * mask] == 1., dtype=torch.int64)
                fn = torch.sum(flat_predictions[true * mask] == 0., dtype=torch.int64)
                fp = torch.sum(flat_predictions[(~true) * mask] == 1., dtype=torch.int64)
                val_tp += tp
                val_fn += fn
                val_fp += fp
            f1, precision, recall = f1_precision_recall(val_tp, val_fp, val_fn)
            print(
                'Epoch [{:3d}]: val_precision: {:.3%} -  val_recall: {:.3%} - val_f1: {:.3%}'
                .format(epoch, precision, recall, f1))
            if f1 > old_f1:
                print('Epoch [{:3d}]: F1 improved from {:.3%} to {:.3%}'.format(epoch, old_f1, f1))
                torch.save(model.state_dict(), str(Path(conf.job_dir) / (model_name + '.pt')))
                old_f1 = f1
            else:
                break


_split = re.compile(r'\n\n+|^_+$|^-+$|^=+|\n[A-Z].*:$|\Z', re.MULTILINE)
_punct = re.compile(r'[.:!,;"\']')


def predict_segment(model: BiLSTM, input_mapper, text):
    if len(text) == 0 or text.isspace():
        return []
    tokens, char_ids, word_ids = input_mapper.transform_text(text)
    predictions = model.predict(char_ids, word_ids)
    start_index = None
    prev_end = None
    for (start, end), prediction in zip(tokens, predictions[0]):
        if prediction == 1:
            if start_index is not None:
                end_punct = _punct.match(text, prev_end)
                if end_punct is not None:
                    prev_end = end_punct.end()
                yield start_index, prev_end
            start_index = start
        prev_end = end
    if start_index is not None and prev_end is not None:
        yield start_index, prev_end


def predict_text(model: BiLSTM, input_mapper, text):
    prev = 0
    for match in _split.finditer(text):
        start = match.start()
        local_text = text[prev:start]
        for ss, se in predict_segment(model, input_mapper, local_text):
            yield prev + ss, prev + se
        prev = match.end()


@processor('biomedicus-sentences',
           human_name="Sentence Detector",
           description="Labels sentences given document text.",
           entry_point=__name__,
           outputs=[
               label_index('sentences')
           ])
class Processor(DocumentProcessor):
    def __init__(self, input_mapper: InputMapping, model: BiLSTM):
        self.input_mapper = input_mapper
        self.model = model

    def process_document(self, document: Document, params: Dict[str, Any]):
        with document.get_labeler('sentences', distinct=True) as add_sentence:
            for start, end in predict_text(self.model, self.input_mapper, document.text):
                add_sentence(start, end)


def bi_lstm_hparams_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--embeddings', type=Path)
    parser.add_argument('--chars-file', type=Path)
    parser.add_argument('--word-length', type=int, default=32,
                        help="number of characters per word.")
    parser.add_argument('--dim-char', type=int, default=30,
                        help="length of learned char embeddings.")
    parser.add_argument('--char-cnn-output-channels', type=int, default=50,
                        help="the number of cnn character filters. if "
                             "concatenate_words_chars = False then this"
                             "parameter is ignored and dim_word is used.")
    parser.add_argument('--char-cnn-kernel-size', type=int, default=4,
                        help="the kernel size (number of character embeddings to look at). ")
    parser.add_argument('--char-lstm-hidden-size', type=int, default=50,
                        help="when using bi-lstm the output dimensionality of the bi-lstm.")
    parser.add_argument('--lstm-hidden-size', type=int, default=32,
                        help="the number of units in the bi-lstm character layer. if "
                             "concatenate_word_chars = False then this parameter is ignored "
                             "and dim_word is used.")
    parser.add_argument('--dropout', type=float, default=.2,
                        help="the input/output dropout for the bi-lstms in the network during "
                             "training.")
    return parser


def training_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--epochs', type=int, default=100,
                        help="number of epochs to run training.")
    parser.add_argument('--validation-split', type=float, default=0.2,
                        help="the fraction of the data to use for validation.")
    parser.add_argument('--batch-size', default=32,
                        help="The batch size to use during training.")
    parser.add_argument('--sequence-length', default=32,
                        help='The sequence size to use during training.')
    parser.add_argument('--job-dir', type=Path, required=True,
                        help="Path to the output directory where logs and models will be "
                             "written.")
    parser.add_argument('--input-directory', type=Path, help="input directory")
    parser.add_argument('--log-name', help='A name for the tensorboard log file / checkpoints.')
    return parser


def train(conf):
    words, vectors = load_vectors(conf.embeddings)
    vectors = np.array(vectors)
    char_mapping = load_char_mapping(conf.chars_file)

    input_mapping = InputMapping(char_mapping, words, conf.word_length)
    model = BiLSTM(conf, characters=len(char_mapping), pretrained=vectors)
    train, validation, pos_weight = input_mapping.load_dataset(conf.input_directory,
                                                               conf.validation_split,
                                                               conf.batch_size,
                                                               conf.sequence_length)
    train_on_data(model, conf, train, validation, pos_weight)


def processor(conf):
    logging.basicConfig(level=logging.INFO)
    logger.info('Loading hparams from: {}'.format(conf.hparams_file))
    with conf.hparams_file.open('r') as f:
        d = yaml.load(f, Loader)

        class Hparams:
            pass
        hparams = Hparams()
        hparams.__dict__.update(d)

    logger.info('Loading word embeddings from: "{}"'.format(conf.embeddings))
    words, vectors = load_vectors(conf.embeddings)
    vectors = np.array(vectors)
    logger.info('Loading chararacters from: {}'.format(conf.chars_file))
    char_mapping = load_char_mapping(conf.chars_file)
    input_mapping = InputMapping(char_mapping, words, hparams.word_length)
    model = BiLSTM(hparams, len(char_mapping), vectors)
    model.train(False)
    logger.info('Loading model weights from: {}'.format(conf.model_file))
    with conf.model_file.open('rb') as f:
        state_dict = torch.load(f)
        model.load_state_dict(state_dict)
    proc = Processor(input_mapping, model)
    run_processor(proc, namespace=conf)


def main(args=None):
    parser = ArgumentParser()
    parser.set_defaults(f=lambda *args: parser.print_help())
    subparsers = parser.add_subparsers()
    training_subparser = subparsers.add_parser('train', parents=[bi_lstm_hparams_parser(),
                                                                 training_parser()])
    training_subparser.set_defaults(f=train)

    config = load_config()
    processor_subparser = subparsers.add_parser('processor', parents=[processor_parser()])
    processor_subparser.add_argument('--embeddings', type=Path, default=Path(config['sentences.wordEmbeddings']),
                                     help='Optional override for the embeddings file to use.')
    processor_subparser.add_argument('--chars-file', type=Path, default=Path(config['sentences.charsFile']),
                                     help='Optional override for the chars file to use')
    processor_subparser.add_argument('--hparams-file', type=Path, default=Path(config['sentences.hparamsFile']),
                                     help='Optional override for model hyperparameters file')
    processor_subparser.add_argument('--model-file', type=Path, default=Path(config['sentences.modelFile']),
                                     help='Optional override for model weights file.')
    processor_subparser.set_defaults(f=processor)

    conf = parser.parse_args(args)
    f = conf.f
    del conf.f

    f(conf)


if __name__ == '__main__':
    main()
