from typing import Dict, Optional

from attr import dataclass

from pydantic_settings.types import Json, ModelLoc, SourceLocProvider, TextLocation


@dataclass
class LocationLookupError(ValueError):
    key: ModelLoc
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


class TextValues(Dict[str, Json]):
    __slots__ = ('location_finder',)

    def __init__(self, finder: SourceLocProvider[TextLocation], **values: Json):
        super().__init__(**values)
        self.location_finder = finder

    def get_location(self, val_loc: ModelLoc) -> TextLocation:
        """
        Maps model location to text location.

        As example, files defines something equal to :code:`{'foo': {'bar': [1, 2]}}`,
        and we assuming that first value in the list is't correct and doesn't
        satisfies some condition. Here we might call

        .. code-block
            `file_values.get_location(['foo', 'bar', 0])`

        which returns point, where value begins and ends.

        :param val_loc: values location described as sequence of keys and reducing it
        over root container with :code:`__getitem__` callable we will access final value
        :raises KeyError: in case if model location could not be found inside file,
        e.g. value not provided by file
        :return: file location description
        """
        return self.location_finder.get_location(val_loc)


class ParsingError(ValueError):
    """
    General wrapper for text parsing errors which also provides error location inside
    a source.

    :var cause: error causer
    :var text_location: error location inside text, in case if None, relates to whole file
    """

    def __init__(self, cause: Exception, text_location: TextLocation = None):
        self.cause = cause
        self.text_location: Optional[TextLocation] = text_location
