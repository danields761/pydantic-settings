from pathlib import Path
from typing import Union, List, Callable, TextIO, Iterable

from attr import dataclass

from pydantic_settings.types import Json


@dataclass
class Document:
    content: Json
    location_finder: 'LocationFinder'


DocumentLoaderCallable = Callable[[Union[str, Path, TextIO]], Document]


@dataclass
class Location:
    line: int
    col: int
    end_line: int
    end_col: int

    def get_snippet(self) -> str:
        raise NotImplementedError


@dataclass
class KeyLookupError(ValueError):
    key: List[Union[str, int]]
    part_pos: int

    def __attrs_post_init__(self):
        self.args = (self.key, self.part_pos)

    def __repr__(self) -> str:
        key_repr = ']['.join(repr(part) for part in self.key)
        return f"Requested key {key_repr} can't be found within document"


class MappingExpectError(KeyLookupError):
    pass


class ListExpectError(KeyLookupError):
    pass


class LocationFinder:
    def lookup_key_loc(self, key: Iterable[Union[str, int]]) -> Location:
        raise NotImplementedError
