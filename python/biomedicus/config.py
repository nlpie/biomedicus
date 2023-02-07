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

import logging
import os

from pathlib import Path

logger = logging.getLogger(__name__)


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
    try:
        d[path] = os.path.expandvars(v)
    except TypeError:
        d[path] = v
    return d


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


def _load_default_config():
    global _DEFAULT_CONFIG
    if _DEFAULT_CONFIG is None:
        with (Path(__file__).parent / 'defaultConfig.yml').open('rb') as f:
            _DEFAULT_CONFIG = _load_config(f)


_DEFAULT_CONFIG = None


def load_config():
    try:
        os.environ['BIOMEDICUS_DATA']
    except KeyError:
        data = Path.home() / '.biomedicus' / 'data'
        os.environ['BIOMEDICUS_DATA'] = str(data)

    potential_paths = []
    try:
        cnf = os.getenv('BIOMEDICUS_CONFIG')
        potential_paths.append(Path(cnf))
    except TypeError:
        pass
    locations = [Path.cwd(), Path.home() / '.biomedicus', Path('/etc/biomedicus/')]
    potential_paths += [location / 'biomedicusConfig.yml' for location in locations]

    for config_path in potential_paths:
        try:
            with config_path.open('rb') as f:
                config = _load_config(f)
                logger.info("Using config loaded from: %s", str(config_path))
                return config
        except FileNotFoundError:
            pass

    logger.info("Using default config.")
    _load_default_config()
    return {k: v for k, v in _DEFAULT_CONFIG.items()}
