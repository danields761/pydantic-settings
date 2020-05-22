import json
import json.scanner
import copy
from functools import partial, wraps

from typing import Tuple, Callable, Any, List, Union, TextIO, Dict

from attr import dataclass

from pydantic_settings.types import Json, ModelLoc, TextLocation
from .common import (
    LocationLookupError,
    MappingExpectError,
    ListExpectError,
    TextValues,
    ParsingError,
)


def _rfind(s: str, sym: str, start: int = None, end: int = None) -> int:
    res = s.rfind(sym, start, end)
    return res


def _create_object_hook(original_value):
    @wraps(original_value)
    def routine(
        s_with_end: Tuple[str, int], *args: Any, **kwargs: Any
    ) -> Tuple[ASTItem, int]:
        s, end = s_with_end
        value, new_end = original_value(s_with_end, *args, **kwargs)

        col = end - _rfind(s, '\n', None, end - 1) - 1
        end_col = new_end - _rfind(s, '\n', None, new_end - 1)

        return (
            ASTItem(
                location=TextLocation(
                    line=s.count('\n', None, end) + 1,
                    col=col,
                    end_line=s.count('\n', None, new_end) + 1,
                    end_col=end_col,
                    pos=end,
                    end_pos=new_end,
                ),
                value=value,
            ),
            new_end,
        )

    return routine


@dataclass
class ASTItem:
    location: TextLocation
    value: 'AstJsonLike'

    @classmethod
    def create(
        cls,
        line: int,
        col: int,
        end_line: int,
        end_col: int,
        val: 'AstJsonLike',
        pos: int = None,
        end_pos: int = None,
    ) -> 'ASTItem':
        return ASTItem(
            TextLocation(line, col, end_line, end_col, pos or 0, end_pos or 0), val
        )

    def get_json_value(self) -> Json:
        if isinstance(self.value, list):
            return [child.get_json_value() for child in self.value]
        if isinstance(self.value, dict):
            return {key: child.get_json_value() for key, child in self.value.items()}
        return self.value


AstJsonLike = Union[None, float, int, str, List[ASTItem], Dict[str, ASTItem]]


def _create_scanner_wrapper(
    scanner: Callable[[str, int], Tuple[Json, int]]
) -> Callable[[str, int], Tuple[ASTItem, int]]:
    @wraps(scanner)
    def wrapper(s: str, idx: int) -> Tuple[ASTItem, int]:
        val, end = scanner(s, idx)
        if isinstance(val, ASTItem):
            return val, end

        line = s.count('\n', None, idx) + 1
        newline_from_left = _rfind(s, '\n', None, idx)
        col = idx - newline_from_left
        end_col = end - newline_from_left

        is_supported = val is None or isinstance(val, (int, float, bool))
        if not is_supported:
            raise ValueError(
                f'unexpected value has been returned from scanner: "{val}" of type {type(val)}'
            )

        return ASTItem(TextLocation(line, col, line, end_col, idx, end), val), end

    return wrapper


class ASTDecoder(json.JSONDecoder):
    def __init__(self):
        from json.decoder import JSONArray, JSONObject, scanstring

        super().__init__()

        self.parse_object = _create_object_hook(JSONObject)
        self.parse_array = _create_object_hook(JSONArray)
        str_parser_wrapper = _create_object_hook(
            lambda s_with_end, strict: scanstring(*s_with_end, strict)
        )
        self.parse_string = lambda s, end, strict: str_parser_wrapper((s, end), strict)

        # Here i'am patching scanner closure, because it's internally refers for
        # itself and it is't configurable.
        # Schema is: 'py_make_scanner' defines '_scan_once', which is referred by
        # 'scan_once' which is result of 'py_make_scanner()' expression.
        # Also copy scanner function here, just in case.
        orig_scanner = copy.deepcopy(json.scanner.py_make_scanner(self))
        try:
            cell = next(
                cell
                for cell in orig_scanner.__closure__
                if callable(cell.cell_contents)
                and cell.cell_contents.__name__ == '_scan_once'
            )
        except StopIteration:
            raise ValueError(
                f'Failed to path {orig_scanner.__name__}, probably their internals'
                f' has been changed'
            )

        self.scan_once = _create_scanner_wrapper(cell.cell_contents)
        # Function closure cells read-only before python 3.7,
        # here using one approach found on internet ...
        _cell_set(cell, self.scan_once)


load = partial(json.load, cls=ASTDecoder)
loads = partial(json.loads, cls=ASTDecoder)


def decode_document(content: Union[str, TextIO]) -> TextValues:
    try:
        if isinstance(content, str):
            tree = loads(content)
        else:
            tree = load(content)
    except json.JSONDecodeError as err:
        raise ParsingError(
            err, TextLocation(err.lineno, err.colno, -1, -1, err.pos, -1)
        )

    if not isinstance(tree.value, dict):
        raise ParsingError(ValueError('document root item must be a mapping'), None)

    return TextValues(_LocationFinder(tree), **tree.get_json_value())


class _LocationFinder:
    def __init__(self, root_item: ASTItem):
        self.root_item = root_item

    def get_location(self, key: ModelLoc) -> TextLocation:
        try:
            return self._get_location(key)
        except LocationLookupError as err:
            # in case of this error __causer__ field will be populated
            # with more specific error, so it might be helpful during debugging
            raise KeyError(key) from err

    def _get_location(self, key: ModelLoc) -> TextLocation:
        curr_item = self.root_item
        for i, key_part in enumerate(key):
            if isinstance(key_part, int) and not isinstance(curr_item.value, list):
                raise ListExpectError(key, i)
            elif isinstance(key_part, str) and not isinstance(curr_item.value, dict):
                raise MappingExpectError(key, i)

            try:
                curr_item = curr_item.value[key_part]
            except (KeyError, IndexError):
                raise LocationLookupError(key, i)

        return curr_item.location


def _make_cell_set_template_code():
    """
    This module was extracted from the `cloud` package, developed by
    PiCloud, Inc.

    Copyright (c) 2015, Cloudpickle contributors.
    Copyright (c) 2012, Regents of the University of California.
    Copyright (c) 2009 PiCloud, Inc. http://www.picloud.com.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the University of California, Berkeley nor the
          names of its contributors may be used to endorse or promote
          products derived from this software without specific prior written
          permission.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
    HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
    TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
    PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
    LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

    Docs stripped, borrowed from here
    https://github.com/cloudpipe/cloudpickle/pull/90/files#diff-d2a3618afedd4e124c532151eedbae09R74
    """
    import types

    def inner(value):
        lambda: cell  # make ``cell`` a closure so that we get a STORE_DEREF
        cell = value

    co = inner.__code__

    # NOTE: we are marking the cell variable as a free variable intentionally
    # so that we simulate an inner function instead of the outer function. This
    # is what gives us the ``nonlocal`` behavior in a Python 2 compatible way.
    return types.CodeType(
        co.co_argcount,
        co.co_kwonlyargcount,
        co.co_nlocals,
        co.co_stacksize,
        co.co_flags,
        co.co_code,
        co.co_consts,
        co.co_names,
        co.co_varnames,
        co.co_filename,
        co.co_name,
        co.co_firstlineno,
        co.co_lnotab,
        co.co_cellvars,  # this is the trickery
        (),
    )


def _cell_set(cell, value):
    """
    Set the value of a closure cell.
    """
    import sys
    import types

    if sys.version_info < (3, 7):
        cell_set_template_code = _make_cell_set_template_code()
        return types.FunctionType(
            cell_set_template_code, {}, '_cell_set_inner', (), (cell,)
        )(value)
    else:
        cell.cell_contents = value


# check that json module is compatible with our implementation
def _check_capability():
    ASTDecoder()


_check_capability()
