from typing import Mapping, Dict, Type, Tuple, List, Union, TypeVar

from pydantic_settings.types import Json


_sentinel = object()


def deep_merge_mappings(
    first_map: Mapping[str, Json], second_map: Mapping[str, Json]
) -> Dict[str, Json]:
    dst: Dict[str, Json] = {}
    keys = set(first_map).union(set(second_map))
    for key in keys:
        first_val = first_map.get(key, _sentinel)
        second_val = second_map.get(key, _sentinel)

        assert first_val is not _sentinel or second_val is not _sentinel

        if first_val is _sentinel and second_val is not _sentinel:
            val = second_val
        else:
            val = first_val

        if isinstance(first_val, Mapping) and isinstance(second_val, Mapping):
            val = deep_merge_mappings(first_val, second_val)

        dst[key] = val

    return dst


def get_generic_info(t: Type) -> Tuple[Type, Tuple[Type, ...]]:
    try:
        return t.__origin__, t.__args__
    except AttributeError:
        raise TypeError(f'{t} is not a generic class')


def get_union_subtypes(t: Type) -> Tuple[Type, ...]:
    origin, args = get_generic_info(t)
    if origin is not Union:
        raise TypeError(f'{t} is not typing.Union')
    return args
