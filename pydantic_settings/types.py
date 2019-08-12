from __future__ import annotations

from typing import Dict, Union, List, Any, TYPE_CHECKING


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
