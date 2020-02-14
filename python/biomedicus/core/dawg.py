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
"""Implementation of a directed acyclic word graph.

"""
from typing import List, Generic, TypeVar, MutableMapping, Iterator, Tuple

__all__ = [
    'DAWG'
]


VT = TypeVar('VT', covariant=True)


class _Node(Generic[VT]):
    def __init__(self):
        self.links = {}


def _find_node(ptr, key):
    for word in key:
        ptr = ptr.links[word]
    return ptr


class DAWG(MutableMapping[List[str], VT], Generic[VT]):

    def __init__(self):
        self.root = _Node()
        self.length = 0

    def __getitem__(self, k: List[str]) -> VT:
        ptr = _find_node(self.root, k)
        try:
            return ptr.value
        except AttributeError:
            raise KeyError('Not found: {}'.format(k))

    def __setitem__(self, k: List[str], v: VT) -> None:
        ptr = self.root
        for word in k:
            try:
                next = ptr.links[word]
            except KeyError:
                next = _Node()
                ptr.links[word] = next
            ptr = next
        if not hasattr(ptr, 'value'):
            self.length += 1
        ptr.value = v

    def __delitem__(self, v: List[str]) -> None:
        ptr = _find_node(self.root, v)
        try:
            del ptr.value
            self.length -= 1
        except AttributeError:
            raise KeyError('Not found: {}'.format(v))

    def __iter__(self) -> Iterator[List[str]]:
        ptr = self.root
        result = []
        stack = []
        i = 0
        words = list(ptr.links.keys())
        while True:
            if hasattr(ptr, 'value'):
                yield list(result)
            if i < len(words):
                stack.append((ptr, i + 1, words))
                word = words[i]
                result.append(word)
                ptr = ptr.links[word]
                words = list(ptr.links.keys())
                i = 0
            elif len(stack) > 0:
                ptr, i, words = stack.pop()
                result.pop()
            else:
                break

    def __len__(self) -> int:
        return self.length

    def matcher(self) -> 'Matcher':
        return Matcher(self)


class Matcher(Generic[VT]):
    def __init__(self, dawg: DAWG[VT]):
        self.dawg = dawg
        self.active = [(0, dawg.root)]

    def advance(self, word: str) -> List[Tuple[int, VT]]:
        new_active = [(0, self.dawg.root)]
        results = []
        for i, (l, ptr) in enumerate(self.active):
            try:
                nptr = ptr.links[word]
                if hasattr(nptr, 'value'):
                    results.append((l + 1, nptr.value))
                new_active.append((l + 1, nptr))
            except KeyError:
                pass
        self.active = new_active
        return results
