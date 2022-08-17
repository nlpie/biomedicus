# Copyright 2022 Regents of the University of Minnesota.
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
import sqlite3

from biomedicus import default_pipeline
from mtap import Event

if __name__ == '__main__':
    parser = ArgumentParser(add_help=True, parents=[default_pipeline.argument_parser()])
    parser.add_argument('input_file')
    args = parser.parse_args()
    with default_pipeline.from_args(args) as pipeline:
        client = pipeline.events_client
        con = sqlite3.connect(args.input_file)
        cur = con.cursor()

        def source():
            for name, text in cur.execute("SELECT NAME, TEXT FROM DOCUMENTS"):
                with Event(event_id=name, client=client) as e:
                    doc = e.create_document('plaintext', text)
                    yield doc

        count, = next(cur.execute("SELECT COUNT(*) FROM DOCUMENTS"))
        pipeline.run_multithread(source(), total=count)
        pipeline.print_times()
        con.close()
