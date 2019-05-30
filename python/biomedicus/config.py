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
import os

from pathlib import Path


def _collapse(d, path, v):
    try:
        p = ''
        if path is not None:
            p = path + '.'
        for k, v in v.items():
            _collapse(d, p + k, v)
        return d
    except AttributeError:
        pass
    except TypeError:
        raise ValueError('Failed to load configuration')

    d[path] = os.path.expandvars(v)
    return d


_DEFAULT_CONFIG = _collapse({}, None, {
    'sentences': {
        'model': 'deep',
        'hparams_file': '${BIOMEDICUS_DATA}/sentences/hparams.yaml',
        'model_file': '${BIOMEDICUS_DATA}/sentences/model.h5',
        'words_list': '${BIOMEDICUS_DATA}/sentences/vocab/words.txt',
        'vocab_dir': '${BIOMEDICUS_DATA}/sentences/vocab/',
    }
})


def _load_config(f):
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    config = load(f, Loader=Loader)
    if not isinstance(config, dict):
        raise TypeError("Failed to load configuration from file: " + str(f))
    return _collapse({}, None, config)


def load_config():
    potential_paths = []
    try:
        cnf = os.getenv('BIOMEDICUS_CONFIG')
        potential_paths.append(Path(cnf))
    except TypeError:
        pass
    locations = [Path.cwd(), Path.home().joinpath('.biomedicus'), Path('/etc/biomedicus/')]
    potential_paths += [location.joinpath('biomedicusConfig.yml') for location in locations]

    for config_path in potential_paths:
        try:
            with config_path.open('rb') as f:
                return _load_config(f)
        except FileNotFoundError:
            pass

    return {k: os.path.expandvars(v) for k, v in _DEFAULT_CONFIG.items()}
