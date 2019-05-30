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
import sys

import nlpnewt
import uuid


def main():
    with nlpnewt.Pipeline() as pipeline:
        pipeline.add_processor('biomedicus-sentences')
        text = sys.stdin.read()
        with nlpnewt.Events() as events:
            with events.open_event(str(uuid.uuid4())) as event:
                document = event.add_document('plaintext', text)
                pipeline.run(document)
                sentences = document.get_label_index('sentences')
                for sentence in sentences:
                    start = int(sentence.start_index)
                    end = int(sentence.end_index)
                    print(text[start:end])
                pipeline.print_times()


if __name__ == '__main__':
    main()
