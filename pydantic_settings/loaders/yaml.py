from contextlib import nullcontext
from pathlib import Path
from typing import Union, TextIO, List

import yaml

from .common import (
    Document,
    LocationFinder,
    Location,
    KeyLookupError,
    MappingExpectError,
    ListExpectError,
)


class _LocationFinder(LocationFinder):
    def __init__(self, root_node: yaml.Node):
        self._node = root_node

    def lookup_key_loc(self, key: List[Union[str, int]]) -> Location:
        node = self._lookup_node_by_loc(key)
        return Location(
            node.start_mark.line + 1,
            node.start_mark.column + 1,
            node.end_mark.line + 1,
            node.end_mark.column + 1,
        )

    def _lookup_node_by_loc(self, key: List[Union[str, int]]) -> yaml.Node:
        curr_node = self._node
        if curr_node is None:
            raise KeyLookupError(key, -1)

        for part_num, key_part in enumerate(key):
            new_node = curr_node
            if not isinstance(curr_node, yaml.CollectionNode):
                raise KeyLookupError(key, part_num)
            if isinstance(key_part, str):
                if not isinstance(curr_node, yaml.MappingNode):
                    raise MappingExpectError(key, part_num)

                for key_node, value_node in curr_node.value:
                    if key_node.value == key_part:
                        new_node = value_node
            else:
                if not isinstance(curr_node, yaml.SequenceNode):
                    raise ListExpectError(key, part_num)

                if len(curr_node.value) < key_part:
                    new_node = curr_node.value[key_part]

            if new_node is curr_node:
                raise KeyLookupError(key, part_num)
            curr_node = new_node

        return curr_node


def load_document(
    content: Union[str, TextIO], *, loader_cls=yaml.SafeLoader
) -> Document:
    if isinstance(content, (str, Path)):
        context = open(content, 'r')
    else:
        context = nullcontext(content)

    with context as stream:
        loader = loader_cls(stream)
        root_node = loader.get_single_node()

        if root_node is None:
            root_node = {}

        return Document(
            loader.construct_document(root_node), _LocationFinder(root_node)
        )
