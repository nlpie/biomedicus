#  Copyright 2022 Regents of the University of Minnesota.
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
from pathlib import Path

from mtap import Event, EventsClient


def rtf_source(input_directory: Path, extension_glob: str, events_client: EventsClient):
    input_directory = Path(input_directory)
    for path in input_directory.rglob(extension_glob):
        with path.open('rb', errors=None) as f:
            rtf = f.read()
        relative = str(path.relative_to(input_directory))
        with Event(event_id=relative, client=events_client, only_create_new=True) as event:
            event.binaries['rtf'] = rtf
            yield event
