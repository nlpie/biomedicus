#  Copyright 2020 Regents of the University of Minnesota.
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
import pytest

from biomedicus.core.dawg import DAWG


def test_create_dawg():
    dawg = DAWG()
    dawg[['a', 'b', 'c']] = True
    dawg[['a', 'b', 'd']] = False
    assert ['a', 'b', 'c'] in dawg
    assert ['a', 'b', 'd'] in dawg
    assert ['a', 'b'] not in dawg
    assert ['a', 'b', 'x'] not in dawg
    assert dawg[['a', 'b', 'c']]
    assert not dawg[['a', 'b', 'd']]


def test_iter():
    dawg = DAWG()
    dawg[['a', 'b', 'c']] = True
    dawg[['a', 'b', 'd']] = False
    assert ['a', 'b', 'c'] in list(dawg)
    assert ['a', 'b', 'd'] in list(dawg)


def test_delete():
    dawg = DAWG()
    dawg[['a', 'b', 'c']] = True
    dawg[['a', 'b', 'd']] = False
    del dawg[['a', 'b', 'd']]
    assert list(dawg) == [['a', 'b', 'c']]
    assert len(dawg) == 1


def test_delete_absent():
    dawg = DAWG()
    dawg[['a', 'b', 'c']] = True
    dawg[['a', 'b', 'd']] = False
    with pytest.raises(KeyError):
        del dawg[['a', 'b']]


def test_matcher():
    dawg = DAWG()
    dawg[['a', 'b', 'c']] = True
    dawg[['a', 'b', 'd']] = False
    matcher = dawg.matcher()
    assert matcher.advance('x') == []
    assert matcher.advance('a') == []
    assert matcher.advance('b') == []
    assert matcher.advance('c') == [(3, True)]
    assert matcher.advance('d') == []
