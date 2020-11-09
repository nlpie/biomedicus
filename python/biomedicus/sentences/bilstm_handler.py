import os
import re
from pathlib import Path

import torch
from ts.torch_handler.base_handler import BaseHandler

_split = re.compile(r'\n\n+|^_+$|^-+$|^=+$|\Z', re.MULTILINE)

_whitespace_pattern = re.compile(r'((?!_)[\w.\'])+|\[\*\*.*?\*\*\]')
_digit = re.compile(r'[0-9]')
_identifier = re.compile(r'\[\*\*.*\*\*\]')
_punct = re.compile(r'[.:!?,;"\'\])]')
_max_sequence_length = 256


def get_char(char_mapping, char):
    return char_mapping.get(char, len(char_mapping))


def step_sequence(char_ids, word_ids, labels, sequence_length):
    length = len(labels)
    required_pad = sequence_length - length
    if required_pad > 0:
        yield char_ids, word_ids, labels
    else:
        for i in range(0, length - sequence_length):
            limit = i + sequence_length
            yield char_ids[i:limit], word_ids[i:limit], labels[i:limit]


def predict(model, char_ids, word_ids):
    if len(char_ids[0]) == 0:
        return torch.empty(1, 0)
    with torch.no_grad():
        logits = model(char_ids, word_ids, torch.tensor([len(char_ids[0])]))
        predictions = torch.round(torch.sigmoid(logits))
        return predictions


class ModelHandler(BaseHandler):
    UNKNOWN_WORD = -1
    PADDING = 0
    TOKEN_BEGIN = 1
    TOKEN_END = 2
    PREV_TOKEN = 3
    NEXT_TOKEN = 4
    BEGIN_SEQUENCE = 5
    END_SEQUENCE = 6

    def load_char_mapping(self, tokens_file):
        char_mappings = {
            'PADDING': self.PADDING,
            'TOKEN_BEGIN': self.TOKEN_BEGIN,
            'TOKEN_END': self.TOKEN_END,
            'PREV_TOKEN': self.PREV_TOKEN,
            'NEXT_TOKEN': self.NEXT_TOKEN,
            'BEGIN_SEQUENCE': self.BEGIN_SEQUENCE,
            'END_SEQUENCE': self.END_SEQUENCE,
            '\n': 7,
            '\t': 8,
            ' ': 9
        }
        with Path(tokens_file).open('r') as f:
            for char in f:
                char_mappings[char[:-1]] = len(char_mappings)
        return char_mappings

    def initialize(self, context):
        self.manifest = context.manifest

        properties = context.system_properties
        model_dir = properties.get("model_dir")
        self.device = torch.device(
            "cuda:" + str(properties.get("gpu_id")) if torch.cuda.is_available() else "cpu")

        serialized_file = self.manifest['model']['serializedFile']
        model_pt_path = os.path.join(model_dir, serialized_file)
        if not os.path.isfile(model_pt_path):
            raise RuntimeError("Missing the model.pt file")

        self.model = torch.load(model_pt_path, map_location=self.device).eval().to(self.device)
        self.model.share_memory()

        words_file = os.path.join(model_dir, "words.txt")
        words = []
        with open(words_file, 'r') as f:
            for line in f:
                words.append(line[:-1])

        chars_file = os.path.join(model_dir, "chars.txt")
        self.char_mapping = self.load_char_mapping(chars_file)
        self.word_mapping = {word: i for i, word in enumerate(words)}
        self.word_length = self.model.hparams['word_length']

        self.initialized = True

    def handle(self, data, context):
        text = data[0]["text"]
        try:
            text = text.decode("utf-8")
        except AttributeError:
            pass
        prev = 0
        results = []
        for match in _split.finditer(text):
            start = match.start()
            local_text = text[prev:start]
            for ss, se in self.predict_segment(local_text):
                results.append((prev + ss, prev + se))
            prev = match.end()
        return [results]

    def transform_text(self, text, device=None):
        char_ids = []
        word_ids = []
        actual_tokens = [(m.start(), m.end()) for m in _whitespace_pattern.finditer(text)]
        tokens = [(0, 0)] + actual_tokens + [(len(text), len(text))]
        start_of_sequence = True
        for i in range(1, len(tokens) - 1):
            local_char_ids, local_word_id = self.transform_word(i, start_of_sequence,
                                                                text, tokens)
            char_ids.append(local_char_ids)
            word_ids.append(local_word_id)
            start_of_sequence = False
        return actual_tokens, torch.tensor([char_ids], device=device), torch.tensor([word_ids],
                                                                                    device=device)

    def transform_word(self, i, start_of_sequence, text, tokens):
        _, prev_end = tokens[i - 1]
        start, end = tokens[i]
        next_start, _ = tokens[i + 1]
        prior = text[prev_end:start]
        word = text[start:end]
        post = text[end:next_start]
        local_char_ids = self.lookup_char_ids(prior, word, post, start_of_sequence)
        local_word_id = self.lookup_word_id(word)
        return local_char_ids, local_word_id

    def lookup_char_ids(self, prior, word, post, start_of_sequence):
        char_ids = ([self.BEGIN_SEQUENCE if start_of_sequence else self.PREV_TOKEN]
                    + [get_char(self.char_mapping, c) for c in prior]
                    + [self.TOKEN_BEGIN]
                    + [get_char(self.char_mapping, c) for c in word]
                    + [self.TOKEN_END]
                    + [get_char(self.char_mapping, c) for c in post]
                    + [self.NEXT_TOKEN])
        if len(char_ids) > self.word_length:
            return char_ids[:self.word_length]
        elif len(char_ids) < self.word_length:
            padded = [self.PADDING for _ in range(self.word_length)]
            padded[:len(char_ids)] = char_ids
            return padded
        else:
            return char_ids

    def lookup_word_id(self, word):
        if _identifier.match(word):
            word = 'IDENTIFIER'
        else:
            word = word.lower()
            word = _punct.sub('', word)
            word = _digit.sub('#', word)
        local_word_id = self.word_mapping.get(word, len(self.word_mapping))
        return local_word_id

    def predict_segment(self, text):
        if len(text) == 0 or text.isspace():
            return torch.empty(1, 0)
        tokens, char_ids, word_ids = self.transform_text(text, device=self.device)

        if len(char_ids) == 0:
            return torch.empty(1, 0)

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
            local_predictions = predict(self.model, char_ids, word_ids)
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
