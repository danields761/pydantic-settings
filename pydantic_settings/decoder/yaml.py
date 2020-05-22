import io
from typing import Union, TextIO

import yaml

from pydantic_settings.types import ModelLoc
from .common import (
    LocationLookupError,
    MappingExpectError,
    ListExpectError,
    TextValues,
    ParsingError,
)
from .. import TextLocation


class _LocationFinder:
    def __init__(self, root_node: yaml.Node):
        self._node = root_node

    def get_location(self, key: ModelLoc) -> TextLocation:
        try:
            node = self._lookup_node_by_loc(key)
        except LocationLookupError as err:
            raise KeyError(key) from err

        return TextLocation(
            node.start_mark.line + 1,
            node.start_mark.column + 1,
            node.end_mark.line + 1,
            node.end_mark.column + 1,
            node.start_mark.pointer,
            node.end_mark.pointer,
        )

    def _lookup_node_by_loc(self, key: ModelLoc) -> yaml.Node:
        curr_node = self._node
        if curr_node is None:
            raise LocationLookupError(key, -1)

        for part_num, key_part in enumerate(key):
            new_node = curr_node
            if not isinstance(curr_node, yaml.CollectionNode):
                raise LocationLookupError(key, part_num)
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
                raise LocationLookupError(key, part_num)
            curr_node = new_node

        return curr_node


def decode_document(
    content: Union[str, TextIO], *, loader_cls=yaml.SafeLoader
) -> TextValues:
    if isinstance(content, str):
        stream = io.StringIO(content)
    else:
        stream = content

    loader = loader_cls(stream)

    try:
        root_node = loader.get_single_node()
        values = loader.construct_document(root_node)
    except yaml.YAMLError as err:
        if not isinstance(err, yaml.MarkedYAMLError):
            loc = None
        else:
            loc = TextLocation(
                err.problem_mark.line + 1,
                err.problem_mark.column + 1,
                -1,
                -1,
                err.problem_mark.pointer,
                -1,
            )

        raise ParsingError(err, loc)

    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ParsingError(ValueError('document root item must be a mapping'), None)

    return TextValues(_LocationFinder(root_node), **values)
