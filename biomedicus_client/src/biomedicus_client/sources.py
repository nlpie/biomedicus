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

"""Input sources for running pipelines."""

import fnmatch
import time
from pathlib import Path
from typing import Iterator

from mtap import Event
from mtap.pipeline import ProcessingSource
from mtap.types import EventsClient
from watchdog.events import FileSystemEventHandler, FileSystemEvent

__all__ = [
    'rtf_source',
    'RtfHandler',
    'TxtHandler',
    'WatcherSource'
]


def rtf_source(input_directory: Path, extension_glob: str, events_client: EventsClient) -> Iterator[Event]:
    input_directory = Path(input_directory)
    for path in input_directory.rglob(extension_glob):
        with path.open('rb', errors=None) as f:
            rtf = f.read()
        relative = str(path.relative_to(input_directory))
        with Event(event_id=relative, client=events_client, only_create_new=True) as event:
            event.binaries['rtf'] = rtf
            yield event


class RtfHandler(FileSystemEventHandler):
    def __init__(self, input_directory: Path, extension_glob: str, events_client: EventsClient):
        self.input_directory = Path(input_directory)
        self.extension_glob = extension_glob
        self.events_client = events_client
        self.consume = None

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            src_path = event.src_path()
            if fnmatch.fnmatch(src_path, self.extension_glob):
                path = Path(src_path)
                with path.open('rb', errors=None) as f:
                    rtf = f.read()
                relative = str(path.relative_to(self.input_directory))
                with Event(event_id=relative,
                           client=self.events_client,
                           only_create_new=True) as event:
                    event.binaries['rtf'] = rtf
                    self.consume(event)


class TxtHandler(FileSystemEventHandler):
    def __init__(self,
                 input_directory: Path,
                 extension_glob: str,
                 events_client: EventsClient,
                 document_name='plaintext'):
        self.input_directory = Path(input_directory)
        self.extension_glob = extension_glob
        self.events_client = events_client
        self.consume = None
        self.document_name = document_name

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            src_path = event.src_path
            if fnmatch.fnmatch(src_path, self.extension_glob):
                print('Processing: ' + src_path)
                path = Path(src_path)
                with path.open('r', errors=None) as f:
                    txt = f.read()
                relative = str(path.relative_to(self.input_directory))
                with Event(event_id=relative, client=self.events_client,
                           only_create_new=True) as e:
                    doc = e.create_document(self.document_name, txt)
                    self.consume(doc)


class WatcherSource(ProcessingSource):
    def __init__(self, handler):
        self.handler = handler

    def produce(self, consume):
        from watchdog.observers import Observer

        self.handler.consume = consume

        observer = Observer()
        observer.schedule(self.handler, str(self.handler.input_directory), recursive=True)
        print('Observing directory: ' + str(self.handler.input_directory))
        observer.start()
        try:
            while True:
                time.sleep(1 * 60 * 60 * 24)
        finally:
            observer.stop()
            observer.join()
