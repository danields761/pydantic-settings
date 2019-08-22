from dataclasses import Field
from typing import Dict, Union, List, Any, ClassVar, Type, Sequence, TypeVar

from pydantic import BaseModel
from typing_extensions import Protocol


Json = Union[float, int, str, Dict[str, Any], List[Any]]
JsonDict = Dict[str, Json]
JsonList = List[Json]


class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


class AttrsProtocol(Protocol):
    __attrs_attrs__: ClassVar[Dict[str, Any]]


AnyModelType = Type[Union[BaseModel, DataclassProtocol, AttrsProtocol]]


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
