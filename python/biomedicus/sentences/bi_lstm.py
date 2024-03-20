#  Copyright (c) Regents of the University of Minnesota.
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
import logging
import re
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from time import time
from typing import Dict, Any

import numpy as np
import torch
import yaml
from mtap import processor_parser, Document, DocumentProcessor, processor, run_processor
from mtap.descriptors import labels
from mtap.processing import Processor
from torch import nn, optim
from torch.nn import functional as F
from torch.nn.utils.rnn import pad_packed_sequence, pack_padded_sequence, \
    PackedSequence

from biomedicus.config import load_config
from biomedicus.deployment import check_data
from biomedicus.sentences.input import InputMapping
from biomedicus.sentences.vocabulary import load_char_mapping, n_chars
from biomedicus.utilities.embeddings import load_vectors

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader as Loader

logger = logging.getLogger("biomedicus.sentences.bi_lstm")


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
        self.lstm = nn.LSTM(concatted_word_rep_features, conf.lstm_hidden_size,
                            bidirectional=True,
                            batch_first=True)
        self.batch_norm = nn.BatchNorm1d(concatted_word_rep_features)

        # projection from hidden to the "begin of sentence" score
        self.hidden2bos = nn.Linear(2 * conf.lstm_hidden_size, 1)
        self.hparams = vars(conf)
        self.dropout = nn.Dropout(p=conf.dropout)

    def forward(self, chars, words, sequence_lengths):
        assert chars.shape[0] == words.shape[0]
        assert chars.shape[1] == words.shape[1]
        # flatten the batch and sequence dims into words (batch * sequence, word_len, 1)
        sequence_lengths, sorted_indices = torch.sort(sequence_lengths, descending=True)
        sequence_lengths = sequence_lengths.cpu()
        chars = chars.index_select(0, sorted_indices)
        words = words.index_select(0, sorted_indices)
        word_chars = pack_padded_sequence(chars, sequence_lengths, batch_first=True)
        # run the char_cnn on it and then reshape back to [batch, sequence, ...]
        char_pools = self.char_cnn(word_chars.data).squeeze(-1)

        # Look up the word embeddings
        words = pack_padded_sequence(words, sequence_lengths, batch_first=True)
        embeddings = self.word_embeddings(words.data)

        # Create word representations from the concatenation of the char-cnn derived representation
        # and the word embedding representation
        word_reps = torch.cat((char_pools, embeddings), -1)

        # bath normalization, batch-normalize all words
        word_reps = self.batch_norm(word_reps)

        # Run LSTM on the sequences of word representations to create contextual word
        # representations
        word_reps = PackedSequence(word_reps, batch_sizes=word_chars.batch_sizes,
                                   sorted_indices=sorted_indices,
                                   unsorted_indices=None)
        contextual_word_reps, _ = self.lstm(word_reps)
        # Project to the "begin of sentence" space for each word
        contextual_word_reps = self.dropout(contextual_word_reps.data)
        bos = self.hidden2bos(contextual_word_reps).squeeze(-1)
        bos, _ = pad_packed_sequence(PackedSequence(bos, batch_sizes=word_chars.batch_sizes,
                                                    sorted_indices=sorted_indices,
                                                    unsorted_indices=None),
                                     batch_first=True)
        return bos


def predict(model, char_ids, word_ids, device):
    if len(char_ids[0]) == 0:
        return torch.empty(1, 0)
    with torch.no_grad():
        logits = model(char_ids, word_ids, torch.tensor([len(char_ids[0])], device=device))
        predictions = torch.round(torch.sigmoid(logits))
        return predictions


class Training:
    def __init__(self, model: BiLSTM, conf, train, validation, pos_weight, device):
        self.model = model
        self.conf = conf
        self.optimizer = optim.Adam(model.parameters())

        self.train = train
        self.validation = validation
        self.pos_weight = torch.tensor(pos_weight)

        self.old_f1 = 0.

        self.device = device

    def run(self):
        model_name = "{}".format(time())

        job_dir = Path(self.conf.job_dir)
        job_dir.mkdir(parents=True, exist_ok=True)
        with (job_dir / (model_name + '.yml')).open('w') as f:
            yaml.dump(self.model.hparams, f)

        old_f1 = 0.
        print('STARTING TRAINING')
        for epoch in [x + 1 for x in range(self.conf.epochs)]:
            self._run_epoch(epoch)
            f1 = self._evaluate(epoch)
            if f1 > old_f1:
                model_path = str(job_dir / (model_name + '.pt'))
                print('Epoch [{}]: F1 improved from {:.3%} to {:.3%}'
                      ', saving model to {}'.format(epoch, old_f1, f1, model_path))
                torch.save(self.model.state_dict(), model_path)
                old_f1 = f1
            else:
                break

    def _run_epoch(self, epoch):
        self.model.train(True)

        last_report = datetime.min
        metrics = torch.tensor([0., 0., 0., 0.], dtype=torch.float64)

        for i, ((char_ids, word_ids), truths, lengths) in enumerate(self.train.batches(), start=1):
            self.model.zero_grad()

            maxlen = truths.shape[1]
            mask = torch.arange(maxlen).view(1, -1) < lengths.view(-1, 1)
            mask = mask.view(-1)

            loss, flat_logits = self._step(char_ids, word_ids, truths, lengths, mask)
            flat_predictions = torch.round(torch.sigmoid(flat_logits))

            tp, fp, fn = confusion_matrix(flat_predictions, truths.view(-1).float(), mask)
            f1, precision, recall = f1_precision_recall(tp, fp, fn)

            metrics = torch.tensor([loss, f1, precision, recall]) + (1 - 0.01) * metrics

            now = datetime.now()
            if (now - last_report).total_seconds() > 1:
                last_report = now

                weighted_count = (1 - (1 - 0.01) ** i) / (1 - (1 - 0.01))
                metric_averages = metrics / weighted_count

                print(
                    '\rEpoch [{}]:  {}/{} - '.format(epoch, i, self.train.n_batches)
                    + ' - '.join(['{}: {:0.3f}'.format(name, value)
                                  for name, value
                                  in zip(['loss', 'f1', 'precision', 'recall'], metric_averages)])
                )

    def _step(self, char_ids, word_ids, labels, lengths, mask):
        # compute the logits for the batch
        logits = self.model(char_ids, word_ids, lengths)
        # compute loss using sequence masking and a special weight for positive labels
        loss_fn = torch.nn.BCEWithLogitsLoss(weight=mask, pos_weight=self.pos_weight)
        flat_logits = logits.view(-1)
        flat_labels = labels.view(-1).float()
        loss = loss_fn(flat_logits, flat_labels)
        l1_regularization = 0.01 * torch.norm(
            torch.cat([x.view(-1) for x in self.model.hidden2bos.parameters()]))
        loss += l1_regularization
        loss.backward()
        self.optimizer.step()
        return loss, flat_logits

    def _evaluate(self, epoch):
        with torch.no_grad():
            self.model.train(False)
            val_tp = torch.tensor(0, dtype=torch.int64)
            val_fn = torch.tensor(0, dtype=torch.int64)
            val_fp = torch.tensor(0, dtype=torch.int64)
            for (char_ids, word_ids), truths, lengths in self.validation.batches():
                # validation batches are shape = [1, sequence_length] with no padding
                predictions = predict(self.model, char_ids, word_ids, device=self.device)
                flat_predictions = predictions.view(-1)
                flat_labels = truths.view(-1)
                # there is no padding in the validation batch
                mask = torch.ones_like(flat_labels, dtype=torch.bool)
                tp, fp, fn = confusion_matrix(flat_predictions, flat_labels, mask)
                val_tp += tp
                val_fn += fn
                val_fp += fp
            f1, precision, recall = f1_precision_recall(val_tp, val_fp, val_fn)
            print(
                'Epoch [{}]: val_precision: {:.3%} -  val_recall: {:.3%} '
                '- val_f1: {:.3%}'.format(epoch, precision, recall, f1)
            )
            return f1


def confusion_matrix(predictions, labels, mask):
    true = labels == 1
    tp = torch.sum(predictions[true * mask] == 1., dtype=torch.int64)
    fp = torch.sum(predictions[(~true) * mask] == 1., dtype=torch.int64)
    fn = torch.sum(predictions[true * mask] == 0., dtype=torch.int64)
    return tp, fp, fn


_split = re.compile(r'\n\n+|^_+$|^-+$|^=+$|\Z', re.MULTILINE)
_punct = re.compile(r'[.:!?,;"\'\])]')
_max_sequence_length = 256


def predict_segment(model: BiLSTM, input_mapper, text, device):
    if len(text) == 0 or text.isspace():
        return []
    with Processor.started_stopwatch('input_mapping'):
        tokens, char_ids, word_ids = input_mapper.transform_text(text)

    if len(char_ids) == 0:
        return []

    all_ids = []
    i = 0
    while i < len(char_ids[0]):
        lim = min(len(char_ids[0]), i + _max_sequence_length)
        if lim - i > 0:
            all_ids.append((
                char_ids[0:1, i:lim],
                word_ids[0:1, i:lim]
            ))
        i += _max_sequence_length
    predictions = []
    for char_ids, word_ids in all_ids:
        with Processor.started_stopwatch('model_predict'):
            local_predictions = predict(model, char_ids, word_ids, device=device)
        predictions.extend(local_predictions[0])
    start_index = None
    prev_end = None
    for (start, end), prediction in zip(tokens, predictions):
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


def predict_text(model: BiLSTM, input_mapper, text, device):
    prev = 0
    with Processor.started_stopwatch('segment_splitting') as split_timer:
        for match in _split.finditer(text):
            split_timer.stop()
            start = match.start()
            local_text = text[prev:start]
            for ss, se in predict_segment(model, input_mapper, local_text, device):
                yield prev + ss, prev + se
            prev = match.end()
            split_timer.start()


@processor('biomedicus-sentences',
           human_name="Sentence Detector",
           description="Labels sentences given document text.",
           outputs=[
               labels('sentences')
           ],
           additional_data={
               'entry_point': __name__,
           })
class SentenceProcessor(DocumentProcessor):
    def __init__(self, input_mapper: InputMapping, model: BiLSTM, device):
        self.input_mapper = input_mapper
        self.model = model
        self.device = device

    def process_document(self, document: Document, params: Dict[str, Any]):
        with torch.no_grad(), document.get_labeler('sentences', distinct=True) as add_sentence:
            for start, end in predict_text(self.model, self.input_mapper, document.text,
                                           self.device):
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
    model = BiLSTM(conf, characters=n_chars(char_mapping), pretrained=vectors)
    train, validation, pos_weight = input_mapping.load_dataset(conf.input_directory,
                                                               conf.validation_split,
                                                               conf.batch_size,
                                                               conf.sequence_length)
    training = Training(model, conf, train, validation, pos_weight)
    training.run()


def create_processor(conf):
    logging.basicConfig(level=logging.INFO)
    check_data(conf.download_data)
    config = load_config()
    if conf.embeddings is None:
        conf.embeddings = Path(config['sentences.wordEmbeddings'])
    if conf.chars_file is None:
        conf.chars_file = Path(config['sentences.charsFile'])
    if conf.hparams_file is None:
        conf.hparams_file = Path(config['sentences.hparamsFile'])
    if conf.model_file is None:
        conf.model_file = Path(config['sentences.modelFile'])
    if conf.torch_device is not None:
        device = conf.torch_device
    else:
        device = "cpu" if conf.force_cpu or not torch.cuda.is_available() else "cuda"
    device = torch.device(device)
    logger.info('Using torch device: "{}"'.format(repr(device)))
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
    logger.info('Loading characters from: {}'.format(conf.chars_file))
    char_mapping = load_char_mapping(conf.chars_file)
    input_mapping = InputMapping(char_mapping, words, hparams.word_length, device=device)
    model = BiLSTM(hparams, n_chars(char_mapping), vectors)
    model.to(device=device)
    logger.info('Loading model weights from: {}'.format(conf.model_file))
    with conf.model_file.open('rb') as f:
        state_dict = torch.load(f)
        model.load_state_dict(state_dict)
    model.eval()
    if conf.mp:
        model.share_memory()
    processor = SentenceProcessor(input_mapping, model, device)
    return processor


def processor(conf):
    processor = create_processor(conf)
    mp_context = None
    if conf.mp:
        mp_context = torch.multiprocessing.get_context(conf.mp_start_method)
    run_processor(processor, options=conf, mp_context=mp_context)


def main(args=None):
    parser = ArgumentParser()
    parser.set_defaults(f=lambda *args: parser.print_help())
    subparsers = parser.add_subparsers()
    training_subparser = subparsers.add_parser('train', parents=[bi_lstm_hparams_parser(),
                                                                 training_parser()])
    training_subparser.set_defaults(f=train)

    processor_subparser = subparsers.add_parser('processor', parents=[processor_parser()])
    processor_subparser.add_argument(
        '--embeddings', type=Path,
        default=None,
        help='Optional override for the embeddings file to use.'
    )
    processor_subparser.add_argument(
        '--chars-file', type=Path,
        default=None,
        help='Optional override for the chars file to use'
    )
    processor_subparser.add_argument(
        '--hparams-file', type=Path,
        default=None,
        help='Optional override for model hyperparameters file'
    )
    processor_subparser.add_argument(
        '--model-file', type=Path,
        default=None,
        help='Optional override for model weights file.'
    )
    processor_subparser.add_argument(
        '--download-data', action="store_true",
        help="Automatically Download the latest model files if they are not found."
    )
    processor_subparser.add_argument(
        '--force-cpu', action="store_true",
        help="Forces pytorch to use the CPU even if CUDA is available."
    )
    processor_subparser.add_argument(
        '--torch-device', default=None,
        help="Optional override to manually set the torch device identifier."
    )
    processor_subparser.set_defaults(f=processor)

    conf = parser.parse_args(args)
    f = conf.f
    del conf.f

    f(conf)


if __name__ == '__main__':
    main()
