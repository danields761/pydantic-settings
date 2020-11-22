from dataclasses import Field
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from attr import dataclass
from pydantic import BaseModel
from typing_extensions import Protocol, runtime_checkable

Json = Union[float, int, str, 'JsonDict', 'JsonList']
JsonDict = Dict[str, Json]
JsonList = List[Json]


@runtime_checkable
class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


@runtime_checkable
class PydanticDataclass(DataclassProtocol, Protocol):
    __initialised__: bool
    __pydantic_model__: ClassVar[BaseModel]

    @classmethod
    def __validate__(
        cls: Type['PydanticDataclass'], value: Any
    ) -> 'PydanticDataclass':
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable]:
        raise NotImplementedError


AnyPydanticModel = Type[Union[BaseModel, PydanticDataclass]]
AnyModelType = Type[Union[BaseModel, DataclassProtocol]]


def is_pydantic_dataclass(cls: Type) -> bool:
    return isinstance(cls, PydanticDataclass)


JsonLocation = Sequence[Union[str, int]]
"""
Sequence of indexes or keys, represents a path to reach the value inside some
:py:obj:`JsonDict`.
"""


@dataclass
class TextLocation:
    """
    Describes value occurrence inside a text.
    """

    line: int
    col: int
    end_line: int
    end_col: int

    pos: int
    end_pos: int


FlatMapLocation = Tuple[str, Optional[TextLocation]]
AnySourceLocation = Union[FlatMapLocation, TextLocation]


SL = TypeVar('SL', contravariant=True)


class SourceValueLocationProvider(Protocol[SL]):
    """
    Describes location of a value inside the source.
    """

    def get_location(self, val_loc: JsonLocation) -> SL:
        raise NotImplementedError


AnySourceLocProvider = Union[
    SourceValueLocationProvider[FlatMapLocation],
    SourceValueLocationProvider[TextLocation],
]
