from dataclasses import Field
from typing import (
    Dict,
    Union,
    List,
    Any,
    ClassVar,
    Type,
    Sequence,
    Generic,
    TypeVar,
    Mapping,
)

from pydantic import BaseModel
from typing_extensions import Protocol


Json = Union[None, float, int, str, Dict[str, Any], List[Any]]
JsonDict = Dict[str, Json]
JsonList = List[Json]


class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


class AttrsProtocol(Protocol):
    __attrs_attrs__: ClassVar[Dict[str, Any]]


AnyModelType = Type[Union[BaseModel, DataclassProtocol, AttrsProtocol]]


ModelLocation = Sequence[Union[str, int]]
"""
Location of a value inside a `JsonDict`, used to describe model input locations
"""


Loc = TypeVar('Loc', contravariant=True)


class ModelLocationGetter(Protocol[Loc]):
    """
    Generic protocol describes a mapping of values
    """

    def get_location(self, val_loc: ModelLocation) -> Loc:
        raise NotImplementedError


class FlatMapValues(Dict[str, Json]):
    __slots__ = 'restored_values', 'restore_errs'

    def __init__(self, restored_values: Dict[ModelLocation, str], **values: Json):
        super().__init__(**values)
        self.restored_values = restored_values

    def get_location(self, val_loc: ModelLocation) -> str:
        """

        :param val_loc:
        :raises KeyError: in case if such value hasn't been restored
        :return:
        """
        return self.restored_values[val_loc]
