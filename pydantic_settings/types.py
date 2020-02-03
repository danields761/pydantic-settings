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
)

from pydantic import BaseModel
from typing_extensions import Protocol, runtime_checkable


Json = Union[float, int, str, Dict[str, Any], List[Any]]
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


ModelLocation = Sequence[Union[str, int]]
"""
Location of a value inside a :py:obj:`JsonDict`, used to describe model input locations
"""


SourceLocation = TypeVar('SourceLocation', contravariant=True)


class SourceLocationProvider(Protocol[SourceLocation]):
    """
    Generic protocol for an object able to describe model field location inside
    a source corresponding to type of :py:obj:`SourceLocation`.
    """

    def get_location(self, val_loc: ModelLocation) -> SourceLocation:
        raise NotImplementedError
