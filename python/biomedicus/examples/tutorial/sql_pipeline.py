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

"""Example SQL pipeline.

Note: This file is in the documentation. Any updates here should be reflected in guides/reading-from-db.md"""

from argparse import ArgumentParser
import sqlite3

from mtap import Event, events_client

from biomedicus_client import default_pipeline

if __name__ == '__main__':
    parser = ArgumentParser(add_help=True, parents=[default_pipeline.argument_parser()])
    parser.add_argument('input_file')
    args = parser.parse_args()
    pipeline = default_pipeline.from_args(args)

    with events_client(pipeline.events_address) as events:
        con = sqlite3.connect(args.input_file)
        cur = con.cursor()

        def source():
            for name, text in cur.execute("SELECT NAME, TEXT FROM DOCUMENTS"):
                with Event(event_id=name, client=events) as e:
                    doc = e.create_document('plaintext', text)
                    yield doc

        count, = next(cur.execute("SELECT COUNT(*) FROM DOCUMENTS"))
        times = pipeline.run_multithread(source(), total=count)
        times.print()
        con.close()
