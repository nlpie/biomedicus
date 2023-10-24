"""Utility code for reading the i2b2 / VA 2010 dataset"""
import re
from argparse import ArgumentParser
from pathlib import Path

from mtap import Event, Pipeline, LocalProcessor, RemoteProcessor, events_client
from mtap.serialization import SerializationProcessor, Serializer

from biomedicus.sentences.one_per_line_sentences import OnePerLineSentencesProcessor

_whitespace_tokenize = re.compile(r'\S+')
_ast_pattern = re.compile(r'^c="(.+?)" (\d+):(\d+) (\d+):(\d+)\|\|t="(.+?)"\|\|a="(.+?)"\n$')


def events(input_directory, target_document, client=None):
    ast_dir = input_directory / 'ast'
    txt_dir = input_directory / 'txt'

    for txt_doc in txt_dir.glob('*.txt'):
        token_map = {}
        txt = ""
        with txt_doc.open('r') as f:
            for line_no, line in enumerate(f, start=1):
                for token_no, token_match in enumerate(_whitespace_tokenize.finditer(line)):
                    token_map[(line_no, token_no)] = (
                        len(txt) + token_match.start(),
                        len(txt) + token_match.end()
                    )
                txt += line

        relative_path = txt_doc.relative_to(txt_dir)
        with Event(event_id=str(relative_path), client=client) as event:
            doc = event.create_document(target_document, txt)
            ast_doc = ast_dir / relative_path.with_suffix('.ast')
            with ast_doc.open('r') as f, doc.get_labeler('i2b2concepts') as label_concept:
                for line in f:
                    match = _ast_pattern.fullmatch(line)
                    concept = match.group(1)
                    start_line = int(match.group(2))
                    start_token = int(match.group(3))
                    end_line = int(match.group(4))
                    end_token = int(match.group(5))
                    concept_type = match.group(6)
                    assertion = match.group(7)
                    label_concept(token_map[(start_line, start_token)][0],
                                  token_map[(end_line, end_token)][1],
                                  concept=concept,
                                  concept_type=concept_type,
                                  assertion=assertion)
            yield doc


def main(args=None):
    parser = ArgumentParser(
        description='Converts files from the i2b2/VA 2010 format to serialized MTAP events '
                    'containing the '
    )
    parser.add_argument('input_directory', type=Path,
                        help='An input directory containing a "txt" folder containing text files '
                             'and an "ast" folder containing the assertions in the i2b2/VA '
                             'pipe-delimited format.')
    parser.add_argument('output_directory', type=Path,
                        help='An output directory to write the serialized mtap events to.')
    parser.add_argument('--target-document', default='plaintext')
    parser.add_argument('--serializer', default='pickle', choices=Serializer._REGISTRY.keys(),
                        help='The serializer to use.')
    parser.add_argument('--events', help="Address of the events client.")
    parser.add_argument('--tagger', help="Address of the pos tagger to use.")

    conf = parser.parse_args(args)

    serializer = Serializer.get(conf.serializer)

    pipeline = Pipeline(
        LocalProcessor(OnePerLineSentencesProcessor(), component_id='sentences'),
        RemoteProcessor('biomedicus-tnt-tagger', address=conf.tagger),
        LocalProcessor(SerializationProcessor(serializer, output_dir=conf.output_directory),
                       component_id='serializer'),
        events_address=conf.events
    )
    with events_client(conf.events) as client:
        times = pipeline.run_multithread(
            events(conf.input_directory, conf.target_document, client=client)
        )
        times.print()


if __name__ == '__main__':
    main()
