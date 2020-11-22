from typing import Dict, Optional

from attr import dataclass

from pydantic_settings.types import (
    Json,
    JsonLocation,
    SourceValueLocationProvider,
    TextLocation,
)


@dataclass
class LocationLookupError(ValueError):
    key: JsonLocation
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

    def __init__(
        self, finder: SourceValueLocationProvider[TextLocation], **values: Json
    ):
        super().__init__(**values)
        self.location_finder = finder

    def get_location(self, val_loc: JsonLocation) -> TextLocation:
        return self.location_finder.get_location(val_loc)


class ParsingError(ValueError):
    """
    General wrapper for text parsing errors which also provides error location
    inside a source.
    """

    cause: Exception
    """Error causer"""

    text_location: TextLocation
    """Error location inside text."""

    def __init__(self, cause: Exception, text_location: TextLocation = None):
        self.cause = cause
        self.text_location: Optional[TextLocation] = text_location
