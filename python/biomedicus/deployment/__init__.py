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
"""Utilities around deploying the BioMedICUS pipeline."""

from biomedicus.deployment._data_downloading import check_data, download_data_to, DownloadDataCommand
from biomedicus.deployment._default import (
    check_data,
    default_deployment_config,
    scaleout_deploy_config,
    deploy,
    deployment_parser,
    DeployCommand
)
from biomedicus.deployment._rtf_to_text import (
    default_rtf_to_text_deployment_config,
    create_rtf_to_text_deployment,
    DeployRtfToTextCommand,
)
