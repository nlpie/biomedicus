# Copyright (c) Regents of the University of Minnesota.
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

"""Example SQL pipeline for rtf conversion only.

Note: This file is in the documentation. Any updates here should be reflected in guides/reading-from-db.md"""

from argparse import ArgumentParser
import sqlite3

from mtap import Event, events_client

from biomedicus_client import rtf_to_text

if __name__ == '__main__':
    parser = ArgumentParser(add_help=True, parents=[rtf_to_text.argument_parser()])
    parser.add_argument('input_file')
    args = parser.parse_args()
    args.rtf = True  # Toggles --rtf flag always on.
    # Can also skip parsing arguments and programmatically create the pipeline,
    # see :func:`rtf_to_text.create`.
    pipeline = rtf_to_text.from_args(args)
    with events_client(pipeline.events_address) as events:
        con = sqlite3.connect(args.input_file)
        cur = con.cursor()

        def source():
            # Note I recommended that RTF documents be stored as BLOBs since most
            # databases do not support storing text in the standard Windows-1252
            # encoding of rtf documents. (RTF documents can actually use different
            # encodings specified by a keyword like \ansicpg1252 at the beginning of
            # the document, but this is uncommon).
            # If you are storing RTF documents ensure that they are initially read from
            # file using the correct encoding [i.e. open('file.rtf', 'r', encoding='cp1252')]
            # before storing in the database, so that special characters are preserved.
            for name, text in cur.execute("SELECT NAME, TEXT FROM DOCUMENTS"):
                with Event(event_id=name, client=events) as e:
                    e.binaries['rtf'] = text
                    # or "e.binaries['rtf'] = text.encode('cp1252')" in TEXT column case
                    yield e

        count, = next(cur.execute("SELECT COUNT(*) FROM DOCUMENTS"))
        # Here we're adding the params since we're calling the pipeline with a source that
        # provides Events rather than documents. This param will tell DocumentProcessors
        # which document they need to process after the rtf converter creates that document.
        times = pipeline.run_multithread(source(), params={'document_name': 'plaintext'}, total=count)
        times.print()
        con.close()
