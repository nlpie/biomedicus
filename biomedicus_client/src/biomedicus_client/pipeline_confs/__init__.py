#  Copyright 2023 Regents of the University of Minnesota.
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
"""Provides importlib.resources Traversable objects for built-in pipeline configuration files."""
from importlib.resources import files

__all__ = ('DEFAULT', 'SCALEOUT', 'RTF_TO_TEXT')

DEFAULT = files(__name__).joinpath("biomedicus_default_pipeline.yml")
SCALEOUT = files(__name__).joinpath("scaleout_pipeline.yml")
RTF_TO_TEXT = files(__name__).joinpath("rtf_to_text_pipeline.yml")
