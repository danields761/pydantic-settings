from __future__ import annotations

from typing import Dict, Union, List


def eval_type(val, globals_=None, locals_=None):
    from typing import _eval_type

    return _eval_type(val, globals_, locals_)


# mypy doesn't support recursive types, but i don't care
Json = Union[None, float, int, str, 'JsonDict', 'JsonList']
JsonDict = Dict[str, Json]
JsonList = List[Json]

# Json = eval_type(Json, globals())
