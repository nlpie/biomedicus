#  Copyright 2021 Regents of the University of Minnesota.
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
from pathlib import Path

from mtap import Pipeline, RemoteProcessor, EventsClient, LocalProcessor
from mtap.io.serialization import SerializationProcessor, JsonSerializer
from mtap.processing import FilesInDirectoryProcessingSource

from biomedicus.palliative.attach_palliative_themes import AttachPalliativeThemesProcessor
from biomedicus.palliative.coalesce_themes import CoalescePalliativeThemesProcessor


def run_themes_pipeline(input_directory, annotations_directory, output_directory):
    events_address = 'localhost:50100'
    with Pipeline(
        RemoteProcessor('biomedicus-sentences', address='localhost:50300'),
        LocalProcessor(
            AttachPalliativeThemesProcessor(annotations_directory)
        ),
        LocalProcessor(
            CoalescePalliativeThemesProcessor(),
        ),
        LocalProcessor(
            SerializationProcessor(JsonSerializer, output_directory)
        ),
        events_address=events_address
    ) as pipeline:
        source = FilesInDirectoryProcessingSource(pipeline.events_client, input_directory)
        pipeline.run_multithread(source, workers=8)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('input_directory', type=Path)
    parser.add_argument('annotations_directory', type=Path)
    parser.add_argument('output_directory', type=Path)
    conf = parser.parse_args(args)
    run_themes_pipeline(conf.input_directory, conf.annotations_directory, conf.output_directory)


if __name__ == '__main__':
    main()
