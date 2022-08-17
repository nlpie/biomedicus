#  Copyright 2019 Regents of the University of Minnesota.
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
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional, Union

from mtap import Pipeline, LocalProcessor, RemoteProcessor
from mtap.io.serialization import get_serializer, SerializationProcessor
from mtap.processing import FilesInDirectoryProcessingSource

from biomedicus.pipeline.sources import rtf_source, WatcherSource, RtfHandler, TxtHandler

default_pipeline_config = str(Path(__file__).parent / 'biomedicus_default_pipeline.yml')


def create(config: Optional[Union[str, Path]] = None,
           *,
           events_addresses: Optional[str] = None,
           rtf: bool = False,
           rtf_address: str = "localhost:50200",
           serializer: Optional[str] = None,
           output_directory: Union[str, Path] = None,
           include_label_text: bool = False, **_) -> Pipeline:
    """The biomedicus default pipeline for processing clinical documents.

    Args
        config (Optional[Union[str, Path]]): A path to an MTAP pipeline configuration YAML file to
            use instead of the default.

    Keyword Args
        events_addresses (Optional[str]): The address (or addresses, comma separated) for the
            events service.
        rtf (bool): Whether to include the rtf processor at the start of the pipeline. The rtf
            processor will convert RTF data stored in the "rtf" Binary on the event to the
            "plaintext" Document.
        rtf_address (str): The address of the remote rtf processor.
        serializer (Optional[str]): An optional serializer (examples: 'json', 'yml', 'pickle').
        output_directory (Optional[Path]): Where the serializer should output the serialized files.

    Returns
        Pipeline

    """
    if config is None:
        config = default_pipeline_config
    pipeline = Pipeline.from_yaml_file(config)

    if events_addresses is not None:
        pipeline.events_address = events_addresses

    if serializer == 'None':
        serializer = None
    if serializer is not None:
        serialization_proc = SerializationProcessor(get_serializer(serializer),
                                                    output_directory,
                                                    include_label_text=include_label_text)
        ser_comp = LocalProcessor(serialization_proc, component_id='serializer')
        pipeline.append(ser_comp)
    if rtf:
        rtf_processor = RemoteProcessor(processor_id='biomedicus-rtf',
                                        address=rtf_address,
                                        params={'output_document_name': 'plaintext'})
        pipeline.insert(0, rtf_processor)
    return pipeline


def argument_parser():
    """The arguments for the default_pipeline from_args function.

    Returns: ArgumentParser

    """
    parser = ArgumentParser(add_help=False, allow_abbrev=True)
    parser.add_argument('--config', default=None,
                        help='Path to the pipeline configuration file.')
    parser.add_argument('--events-addresses', default=None,
                        help="The address (or addresses, comma separated) for the events service.")
    parser.add_argument('--output_directory', '-o', default='output',
                        help="The output directory to write serializer output to.")
    parser.add_argument('--serializer', default='json',
                        choices=['json', 'yml', 'pickle', 'None'],
                        help="The identifier for the serializer to use, see MTAP serializers.")
    parser.add_argument('--include-label-text', action='store_true',
                        help="Flag to include the covered text for every label")
    parser.add_argument('--rtf', action='store_true',
                        help="Flag to use a source for the rtf reader instead of plain text.")
    parser.add_argument('--rtf-address', default="localhost:50200",
                        help="The address (or addresses, comma separated) for the"
                             "rtf to text converter processor.")
    return parser


def from_args(args: Namespace):
    """Creates a default biomedicus pipeline from arguments.

    Args:
        args (Namespace): The parsed arguments from the argument_parser function or a child of it.

    Returns: Pipeline

    """
    if not isinstance(args, Namespace):
        raise ValueError('"args" parameter should be the parsed arguments from '
                         '"default_pipeline.argument_parser()"')
    return create(**vars(args))


def run_parser():
    """The argument parser for running the default biomedicus pipeline.

    Returns: ArgumentParser object.

    """
    parser = ArgumentParser(add_help=False, parents=[argument_parser()])
    parser.add_argument('input_directory', help="The input directory of text files to process.")
    parser.add_argument('--extension-glob', default=None,
                        help="The extension glob used to find files to process.")
    parser.add_argument('--watch', default=False, action='store_true',
                        help="Watches the directory for new files to process.")
    return parser


def run(args: Namespace):
    with from_args(args) as pipeline:
        input_directory = args.input_directory
        client = pipeline.events_client
        if args.rtf:
            extension_glob = args.extension_glob or "**/*.rtf"
            if args.watch:
                source = WatcherSource(RtfHandler(input_directory, extension_glob, client))
            else:
                source = rtf_source(input_directory, extension_glob, client)
            params = {'document_name': 'plaintext'}
        else:
            extension_glob = args.extension_glob or "**/*.txt"
            if args.watch:
                source = WatcherSource(TxtHandler(input_directory, extension_glob, client))
            else:
                source = FilesInDirectoryProcessingSource(client,
                                                          input_directory,
                                                          extension_glob=extension_glob)
            params = None
        pipeline.run_multithread(source, params=params)
        pipeline.print_times()
