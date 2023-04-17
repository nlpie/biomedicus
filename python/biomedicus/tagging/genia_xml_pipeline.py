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
from argparse import ArgumentParser
from xml.etree import ElementTree

from mtap import Event, GenericLabel, Document, Pipeline, RemoteProcessor, events_client


class DocumentBuilder:
    def __init__(self):
        self.length = 0
        self.text = []
        self.sentences = []
        self.tags = []

    def add_sentence(self, sentence):
        sentence_start = self.length
        end = None
        frag = None
        for word in sentence.findall('w'):
            if frag is None:
                start = self.length
                text = word.text
            else:
                text = frag + word.text
            tag = word.get('c')
            if '|' in tag:
                tag = tag.split('|')[0]
            if tag == '*':
                frag = text
                continue

            self.text.append(text)
            end = start + len(text)
            self.tags.append(GenericLabel(start_index=start, end_index=end, tag=tag))
            self.length = end + 1
        if end is not None:
            self.sentences.append(GenericLabel(start_index=sentence_start, end_index=end))

    def build_doc(self, event):
        text = ' '.join(self.text)
        d = Document(document_name='plaintext', text=text)
        event.add_document(d)
        d.add_labels('pos_tags', self.tags, distinct=True)
        d.add_labels('sentences', self.sentences, distinct=True)
        return d


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input', metavar='INPUT_FILE', help='The input GENIA XML file.')
    parser.add_argument('--events', metavar='EVENTS', default=None,
                        help='The address of the events service.')
    parser.add_argument('--tnt-trainer', metavar='TRAINER', default=None,
                        help='The address of the TnT trainer.')
    args = parser.parse_args(args)
    etree = ElementTree.parse(args.input)
    set = etree.getroot()
    pipeline = Pipeline(
        RemoteProcessor('biomedicus-tnt-trainer', address=args.tnt_trainer),
        events_address=args.events
    )
    with events_client(address=args.events) as client:
        for article in set.findall('article'):
            id = list(article.find('articleinfo'))[0].text
            with Event(event_id=id, client=client) as event:
                db = DocumentBuilder()
                for sentence in (article.find('title').findall('sentence')
                                 + article.find('abstract').findall('sentence')):
                    db.add_sentence(sentence)
                d = db.build_doc(event)
                pipeline.run(d)


if __name__ == '__main__':
    main()
