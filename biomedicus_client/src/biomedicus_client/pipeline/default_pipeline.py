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
"""Support for creating and running the biomedicus default pipeline."""

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional, Union

from importlib_resources import files
from mtap import Pipeline, LocalProcessor, RemoteProcessor
from mtap.serialization import get_serializer, SerializationProcessor

__all__ = ['default_pipeline_config', 'scaleout_pipeline_config', 'create', 'from_args', 'argument_parser']

default_pipeline_config = files('biomedicus_client.pipeline').joinpath('biomedicus_default_pipeline.yml')
scaleout_pipeline_config = files('biomedicus_client.pipeline').joinpath('scaleout_pipeline_config.yml')


def create(config: Optional[Union[str, Path]] = None,
           *, events_addresses: Optional[str] = None,
           rtf: bool = False,
           rtf_address: str = "localhost:50200",
           serializer: Optional[str] = None,
           output_directory: Union[str, Path] = None,
           include_label_text: bool = False,
           address: Optional[str] = None,
           **_) -> Pipeline:
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
        address (Optional[str]): An optional address to use for all processors.

    Returns
        Pipeline

    """
    if config is None:
        config = default_pipeline_config
    pipeline = Pipeline.from_yaml_file(config)

    if events_addresses is not None:
        pipeline.events_address = events_addresses

    serializer = None if serializer == 'None' else serializer
    if serializer is not None:
        serialization_proc = SerializationProcessor(get_serializer(serializer),
                                                    output_directory,
                                                    include_label_text=include_label_text)
        ser_comp = LocalProcessor(serialization_proc, component_id='serializer')
        pipeline.append(ser_comp)

    if rtf:
        rtf_processor = RemoteProcessor(processor_name='biomedicus-rtf',
                                        address=rtf_address,
                                        params={'output_document_name': 'plaintext'})
        pipeline.insert(0, rtf_processor)

    if address is not None:
        pipeline.events_address = address
        for proc in pipeline:
            if isinstance(proc, RemoteProcessor):
                proc.address = address

    return pipeline


def argument_parser() -> ArgumentParser:
    """The arguments for the default_pipeline from_args function.

    Returns: ArgumentParser
    """
    parser = ArgumentParser(add_help=False, allow_abbrev=True)
    parser.add_argument(
        '--config',
        default=None,
        help='Path to the pipeline configuration file.'
    )
    parser.add_argument(
        '--events-addresses',
        default=None,
        help="The address (or addresses, comma separated) for the events service."
    )
    parser.add_argument(
        '--serializer',
        default='json',
        choices=['json', 'yml', 'pickle', 'None'],
        help="The identifier for the serializer to use, see MTAP serializers."
    )
    parser.add_argument(
        '--output_directory', '-o',
        default='output',
        help="The output directory to write serializer output to."
    )
    parser.add_argument(
        '--include-label-text',
        action='store_true',
        help="Flag to include the covered text for every label"
    )
    parser.add_argument(
        '--rtf',
        action='store_true',
        help="Flag to use a source for the rtf reader instead of plain text."
    )
    parser.add_argument(
        '--rtf-address',
        default="localhost:50200",
        help="The address (or addresses, comma separated) for the rtf to text converter processor."
    )
    parser.add_argument(
        '--address', '-a',
        help="An address override, used for the dockerized BioMedICUS."
    )
    return parser


def from_args(args: Namespace) -> Pipeline:
    """Creates a default biomedicus pipeline from arguments.

    Args:
        args (Namespace): The parsed arguments from the argument_parser function or a child of it.

    Returns: Pipeline

    """
    if not isinstance(args, Namespace):
        raise ValueError('"args" parameter should be the parsed arguments from '
                         '"default_pipeline.argument_parser()"')
    return create(**vars(args))
