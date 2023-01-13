#  Copyright 2020 Regents of the University of Minnesota.
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
from argparse import ArgumentParser
from typing import NamedTuple, Optional, Tuple

from mtap import GenericLabel, Event, EventsClient
from mtap.serialization import PickleSerializer


class ConllUEntry(NamedTuple('ConllUEntry', [
    ('id', int),
    ('form', str),
    ('lemma', str),
    ('upos', str),
    ('xpos', Optional[str]),
    ('feats', Optional[str]),
    ('head', int),
    ('deprel', str),
    ('deps', Optional[str]),
    ('misc', Optional[str])
])):
    @staticmethod
    def parse_line(line: str) -> 'ConllUEntry':
        splits = line.split('\t')
        args = []
        for i, arg in enumerate(splits):
            if arg == '_':
                arg = None
            if i in (0, 6) and arg is not None:
                arg = int(arg)
            args.append(arg)
        return ConllUEntry(*args)


class DocumentBuilder:
    def __init__(self, client: EventsClient):
        self.client = client
        self.txt = ''
        self.all_deps = []
        self.sentences = []
        self.pos_tags = []
        self.norms = []
        self.sentence_start = 0

    def add_sentence(self, end_index):
        self.sentences.append(GenericLabel(self.sentence_start, end_index))
        self.txt = self.txt + '\n'
        self.sentence_start = len(self.txt)

    def add_token(self, start_index, end_index, upos, lemma):
        self.pos_tags.append(GenericLabel(start_index, end_index, tag=upos))
        self.norms.append(GenericLabel(start_index, end_index, norm=lemma))

    def add_deps(self, deps):
        self.all_deps.extend(deps)

    def append_text(self, txt: str):
        self.txt = self.txt + txt

    def create_document(self):
        with Event(client=self.client) as e:
            document = e.create_document('plaintext', self.txt)
            document.add_labels('gold_dependencies', self.all_deps)
            document.add_labels('sentences', self.sentences)
            document.add_labels('pos_tags', self.pos_tags)
            document.add_labels('norm_forms', self.norms)
            yield document

    def append_token(self, text: str) -> Tuple[int, int]:
        begin = len(self.txt)
        self.txt = self.txt + text
        end = len(self.txt)
        self.txt = self.txt + ' '
        return begin, end


def read_into_documents(conllu_document: str, client: EventsClient = None, sentences_per_document: int = 15):
    entries = []
    end = None
    sentences = 0
    document_builder = DocumentBuilder(client)
    for line in conllu_document.splitlines():
        if len(line) == 0:
            if len(entries) == 0:
                continue
            # empty line - new sentence
            entries.sort(key=lambda x: x[0].head)
            assert end is not None
            dep_map = {}
            document_builder.add_sentence(end)
            for entry, token_begin, token_end in entries:
                head = dep_map.get(entry.head, None)
                dep = GenericLabel(token_begin, token_end, head=head, deprel=entry.deprel)
                dep.reference_cache['dependents'] = []
                dep_map[entry.id] = dep
                if head is not None:
                    head.dependents.append(dep)
                document_builder.add_token(token_begin, token_end, entry.upos, entry.lemma)
            entries = []
            document_builder.add_deps(dep_map.values())
            sentences += 1
            if sentences == sentences_per_document:
                yield from document_builder.create_document()
                document_builder = DocumentBuilder(client)
                sentences = 0
        else:
            # parse token
            entry = ConllUEntry.parse_line(line)
            begin, end = document_builder.append_token(entry.form)
            entries.append((entry, begin, end))
    if sentences > 0:
        yield from document_builder.create_document()


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    conf = parser.parse_args(args)
    with open(conf.input_file, 'r') as io:
        conllu_document = io.read()
    for document in read_into_documents(conllu_document):
        PickleSerializer.event_to_file(document.event, conf.output_file + '/' + document.event.event_id + '.pickle')


if __name__ == '__main__':
    main()
