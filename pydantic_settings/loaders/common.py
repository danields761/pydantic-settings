from __future__ import annotations

from attr import dataclass
from typing import Union, List


@dataclass
class Location:
    line: int
    col: int
    end_line: int
    end_col: int


class ASTTreeRoot:
    def lookup_key_loc(self, key: List[Union[str, int]]) -> Location:
        raise NotImplementedError
