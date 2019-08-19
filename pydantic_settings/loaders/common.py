from typing import Union, Callable, TextIO, Dict, Optional

from attr import dataclass

from pydantic_settings.types import Json, ModelLocation, ModelLocationGetter


@dataclass
class FileLocation:
    line: int
    col: int
    end_line: int
    end_col: int

    def get_snippet(self) -> str:
        raise NotImplementedError


@dataclass
class LocationLookupError(ValueError):
    key: ModelLocation
    part_pos: int

    def __attrs_post_init__(self):
        self.args = (self.key, self.part_pos)

    def __repr__(self) -> str:
        key_repr = ']['.join(repr(part) for part in self.key)
        return f"Requested key {key_repr} can't be found within document"


class MappingExpectError(LocationLookupError):
    pass


class ListExpectError(LocationLookupError):
    pass


class FileValues(Dict[str, Json]):
    __slots__ = ('location_finder',)

    def __init__(self, finder: ModelLocationGetter[FileLocation], **values: Json):
        super().__init__(**values)
        self.location_finder = finder

    def get_location(self, val_loc: ModelLocation) -> FileLocation:
        """
        Maps model location to file location.

        As example, files defines something equal to "{'foo': {'bar': [1, 2]}}", and we assuming that first
        value in the list is't correct and doesn't satisfies some condition. Here we might
        call `file_values.get_location(['foo', 'bar', 0])` and retrieve point, where value begins and ends.

        :param val_loc: values location described as sequence of keys and reducing it over root container with
        `__getitem__` callable we will access final value
        :raises KeyError: in case if model location could not be found inside file, e.g. value not
        provided by file
        :return: file location description
        """
        return self.location_finder.get_location(val_loc)


class ParsingError(ValueError):
    """
    General wrapper for file parsing errors which also provides error location inside file

    :var cause: error causer
    :var file_location: error location inside file, in case if None, relates to whole file
    """

    def __init__(self, cause: Exception, file_location: FileLocation = None):
        self.cause = cause
        self.file_location: Optional[FileLocation] = file_location


@dataclass
class LoaderMeta:
    name: str
    values_loader: Callable[[Union[str, TextIO]], FileValues]
