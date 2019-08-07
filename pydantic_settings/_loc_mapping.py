from __future__ import annotations

from itertools import takewhile, count
from typing import Tuple, List, Iterator, Union, Dict
from string import ascii_letters, digits, whitespace
from enum import IntEnum, auto

from attr import dataclass


_letters_set = set(ascii_letters + digits)
_whitespaces = set(whitespace)

"""
{
    "val": 12341,
}
"""


@dataclass(slots=True)
class SymbolLocation:
    lineno: int
    coloffset: int
    end_lineno: int
    end_coloffset: int

    @classmethod
    def from_locs(cls, start: Tuple[int, int], end: Tuple[int, int]) -> SymbolLocation:
        return cls(
            lineno=start[0], coloffset=start[1], end_lineno=end[0], end_coloffset=end[1]
        )


class _ContentIterator:
    def __init__(self, content: str):
        self.content = content
        self.curr = None
        self.line = 1
        self.col = 1
        self.pos = 0

    def overtake(self, *, _offset: int = 1) -> Iterator[str]:
        for i in range(self.pos + _offset, len(self.content)):
            if _offset == 0:
                self.curr = self.content[self.pos]
                if self.curr == '\n':
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
            yield self.content[self.pos + _offset]
            self.pos += 1

    def __iter__(self):
        return self.overtake(_offset=0)

    def __next__(self) -> str:
        return next(self.overtake(_offset=0))

    def peek(self) -> str:
        return self.curr

    def get_loc(self) -> Tuple[int, int]:
        return self.line, self.col

    def __repr__(self):
        lines = self.content.split('\n')
        line = self.line - 1
        col = self.col - 1
        return '\n'.join(lines[:line] + [' ' * col + '^'] + lines[line:])


_SymtableType = Dict[List[Union[str, int]], SymbolLocation]


class JSONSymtable:
    def __init__(self, json_content: str):
        self._table: _SymtableType = build_symtable(json_content)

    def lookup_symbol(self, symbol: List[Union[str, int]]) -> SymbolLocation:
        try:
            return self._table[symbol]
        except KeyError:
            raise ValueError(f'no such symbol in table: {symbol}')


def build_symtable(json_content: str) -> _SymtableType:
    table = {}
    _consume_any_value(_ContentIterator(json_content), [], table)
    return table


def _consume_whitespaces(iterator: _ContentIterator):
    for curr in iterator.overtake():
        if curr not in _whitespaces:
            return

    raise ValueError('EOF occurs before key end')


def _consume_key(iterator: _ContentIterator) -> str:
    return ''.join(takewhile(lambda val: val != '"', iterator.overtake()))


def _consume_simple_value(iterator: _ContentIterator):
    for curr in iterator.overtake():
        if curr not in _letters_set:
            return

    raise ValueError('EOF occurs before key end')


def _consume_list(
    iterator: _ContentIterator, path: List[Union[str, int]], symtable: _SymtableType
):
    for num in count():
        _consume_whitespaces(iterator)
        curr = iterator.peek()
        if curr == ',':
            continue
        elif curr == ']':
            return
        else:
            _consume_any_value(iterator, path + [num], symtable)


def _consume_obj(
    iterator: _ContentIterator, path: List[Union[str, int]], symtable: _SymtableType
):
    while True:
        _consume_whitespaces(iterator)
        curr = iterator.peek()
        if curr == '"':
            key = _consume_key(iterator)
            _consume_whitespaces(iterator)
            curr = iterator.peek()
            if curr != ':':
                raise ValueError('Expecting ":" after key')
            _consume_whitespaces(iterator)
            curr = iterator.peek()
            if curr == ',':
                raise ValueError('unexpected comma while waiting for any value')
            elif curr == '}':
                raise ValueError('unexpected object end while waiting for any value')
            else:
                _consume_any_value(iterator, path + [key], symtable)
        elif curr == '}':
            return
        else:
            raise ValueError('expecting key definition after beginning of the object')


def _consume_any_value(
    iterator: _ContentIterator, path: List[Union[str, int]], symtable: _SymtableType
):
    _consume_whitespaces(iterator)
    curr = iterator.peek()
    if curr == '[' or curr == '{':
        loc_start = iterator.get_loc()

        if curr == '[':
            _consume_list(iterator, path, symtable)
        elif curr == '{':
            _consume_obj(iterator, path, symtable)

        loc_end = iterator.get_loc()
        symtable[path] = SymbolLocation.from_locs(loc_start, loc_end)
    else:
        _consume_simple_value(iterator)
