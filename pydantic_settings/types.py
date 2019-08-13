from __future__ import annotations

from dataclasses import Field
from typing import Dict, Union, List, Any, TYPE_CHECKING, ClassVar, Type

from pydantic import BaseModel
from typing_extensions import Protocol


if not TYPE_CHECKING:
    # pydantic supports recursive  types
    # but they still causing some issues when
    # computing type hashes in typing module
    Json = Union[None, float, int, str, 'JsonDict', 'JsonList']
    JsonDict = Dict[str, Json]
    JsonList = List[Json]
else:
    Json = Union[None, float, int, str, Dict[str, Any], List[Any]]
    JsonDict = Dict[str, Json]
    JsonList = List[Json]


class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


class AttrsProtocol(Protocol):
    __attrs_attrs__: ClassVar[Dict[str, Any]]


AnyModelType = Type[Union[BaseModel, DataclassProtocol, AttrsProtocol]]
