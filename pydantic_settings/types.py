from dataclasses import Field
from typing import (
    Dict,
    Union,
    List,
    Any,
    ClassVar,
    Type,
    Sequence,
    TypeVar,
    Iterator,
    Callable,
    Tuple,
    Optional,
)

from attr import dataclass
from pydantic import BaseModel
from typing_extensions import Protocol


Json = Union[float, int, str, 'JsonDict', 'JsonList']
JsonDict = Dict[str, Json]
JsonList = List[Json]


class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


class AttrsProtocol(Protocol):
    __attrs_attrs__: ClassVar[Dict[str, Any]]


class PydanticDataclass(DataclassProtocol, Protocol):
    __initialised__: bool
    __pydantic_model__: ClassVar[BaseModel]

    @classmethod
    def __validate__(cls: Type['PydanticDataclass'], value: Any) -> 'PydanticDataclass':
        raise NotImplementedError

    @classmethod
    def __get_validators__(cls) -> Iterator[Callable]:
        raise NotImplementedError


AnyPydanticModel = Type[Union[BaseModel, PydanticDataclass]]
AnyModelType = Type[Union[BaseModel, DataclassProtocol, AttrsProtocol]]


def is_pydantic_dataclass(cls: Type) -> bool:
    return hasattr(cls, '__pydantic_model__')


ModelLoc = Sequence[Union[str, int]]
"""
Location of a value inside a :py:obj:`JsonDict`, used to describe model input locations
"""


@dataclass
class TextLocation:
    """
    Describes symbol occurrence inside a text
    """

    line: int
    col: int
    end_line: int
    end_col: int

    pos: int
    end_pos: int


FlatMapLoc = Tuple[str, Optional[TextLocation]]
AnySourceLoc = Union[FlatMapLoc, TextLocation]


SourceLocT = TypeVar('SourceLocT', contravariant=True)


class SourceLocProvider(Protocol[SourceLocT]):
    """
    Aimed to describe location of a model field inside some source. Generic
    type variable `SourceLocT` will correspond to the type of a source.
    """

    def get_location(self, val_loc: ModelLoc) -> SourceLocT:
        raise NotImplementedError


AnySourceLocProvider = Union[
    SourceLocProvider[FlatMapLoc], SourceLocProvider[TextLocation]
]
