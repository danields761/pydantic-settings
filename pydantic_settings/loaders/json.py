from __future__ import annotations

import json
import json.scanner
from functools import partial, wraps

from attr import dataclass
from typing import Tuple, Callable, Any

from ..types import Json
from .common import Location


@dataclass
class ASTItem:
    location: Location
    value: Json

    @classmethod
    def create(
        cls, val: Json, line: int, col: int, end_line: int, end_col: int
    ) -> ASTItem:
        return ASTItem(Location(line, col, end_line, end_col), val)


_CreateObjRoutineType = Callable[[str, int, bool, Callable], Tuple[Json, int]]
_CreateASTObjRoutineType = Callable[[str, int, bool, Callable], Tuple[ASTItem, int]]


def _create_object_hook_for_type(original_value):
    def routine(
        s_with_end: Tuple[str, int], *args: Any, **kwargs: Any
    ) -> Tuple[ASTItem, int]:
        s, end = s_with_end
        value, new_end = original_value(s_with_end, *args, **kwargs)

        col = end - _rfind(s, '\n', None, end)
        if col == 0:
            col = 1
        end_col = new_end - _rfind(s, '\n', None, new_end)
        if end_col == 0:
            end_col = 1

        return (
            ASTItem(
                location=Location(
                    line=s.count('\n', None, end) + 1,
                    col=col,
                    end_line=s.count('\n', None, new_end) + 1,
                    end_col=end_col,
                ),
                value=value,
            ),
            new_end,
        )

    return routine


def _rfind(s: str, sym: str, start: int = None, end: int = None) -> int:
    res = s.rfind(sym, start, end)
    if res == -1:
        return 0
    return res


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
        if col == 0:
            col = 1
        end_col = end - newline_from_left

        is_supported = val is None or isinstance(val, (int, float, bool))
        if not is_supported:
            raise ValueError(
                f'unexpected value has been returned from scanner: "{val}" of type {type(val)}'
            )

        return ASTItem(Location(line, col, line, end_col), val), end

    return wrapper


class ASTDecoder(json.JSONDecoder):
    def __init__(self):
        from json.decoder import JSONArray, JSONObject, scanstring

        super().__init__()

        self.parse_object = _create_object_hook_for_type(JSONObject)
        self.parse_array = _create_object_hook_for_type(JSONArray)
        str_parser_wrapper = _create_object_hook_for_type(scanstring)
        self.parse_string = lambda s, end, strict: str_parser_wrapper(
            (s, end),
            lambda s_with_end, strict_: scanstring(
                s_with_end[0], s_with_end[1], strict_
            ),
        )

        # here i'am patching scanner closure, because it's internally refers for
        # itself and it is't configurable.
        # schema is: 'py_make_scanner' defines '_scan_once', which is referred by 'scan_once' which
        # is result of 'py_make_scanner()' expression
        orig_scanner = json.scanner.py_make_scanner(self)
        try:
            cell = next(
                cell
                for cell in orig_scanner.__closure__
                if callable(cell.cell_contents)
                and cell.cell_contents.__name__ == '_scan_once'
            )
        except StopIteration:
            raise ValueError(
                f'Failed to path {orig_scanner.__name__}, probably their internals has been changed'
            )

        self.scan_once = _create_scanner_wrapper(cell.cell_contents)
        cell.cell_contents = self.scan_once


load = partial(json.load, cls=ASTDecoder)
loads = partial(json.loads, cls=ASTDecoder)
