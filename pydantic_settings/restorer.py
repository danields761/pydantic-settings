from collections import defaultdict
from dataclasses import is_dataclass
from functools import reduce
from typing import (
    Any,
    Callable,
    Mapping,
    Optional,
    Dict,
    List,
    Tuple,
    Type,
    cast,
    Iterator,
    Union,
    Sequence,
    NamedTuple,
)
from attr import has as is_attr_class
from pydantic import BaseModel

from pydantic_settings.decoder import TextValues, ParsingError
from pydantic_settings.types import JsonDict, AnyModelType, Json, ModelLoc, FlatMapLoc
from pydantic_settings.utils import get_union_subtypes


_RecStrDictValue = Union['_RecStrDict', str]
_RecStrDict = Dict[str, _RecStrDictValue]


class _FieldLocDescription(NamedTuple):
    path: Tuple[str, ...]
    is_complex: bool
    is_determined: bool


def _noop(val: Any) -> Any:
    return val


def _is_determined_complex_field(field_type: Any) -> bool:
    """Returns flag indicates that field of given type have known set of child fields"""
    return (
        is_attr_class(field_type)
        or is_dataclass(field_type)
        or (isinstance(field_type, type) and issubclass(field_type, BaseModel))
    )


def _estimate_field_complexity(field_type: Any) -> Tuple[bool, bool]:
    if _is_determined_complex_field(field_type):
        return True, True

    try:
        union_subtypes = get_union_subtypes(field_type)
    except TypeError:
        pass
    else:
        return reduce(
            lambda prev, item: (prev[0] or item, prev[1] and item),
            (_is_determined_complex_field(subtype) for subtype in union_subtypes),
            (False, True),
        )

    return False, False


def _list_fields(type_: Type) -> Iterator[Tuple[str, Type]]:
    try:
        union_subtypes = get_union_subtypes(type_)
    except TypeError:
        pass
    else:
        for subtype in union_subtypes:
            try:
                yield from _list_fields(subtype)
            except TypeError:
                pass
        return

    if isinstance(type_, type) and issubclass(type_, BaseModel):
        for field in type_.__fields__.values():
            yield field.name, field.type_
    elif is_attr_class(type_):
        for field in type_.__attrs_attrs__:
            yield field.name, field.type
    elif is_dataclass(type_):
        for field in type_.__dataclass_fields__.values():
            yield field.name, field.type
    else:
        raise TypeError(f"{type_} value isn't a model type")


def _traveler(
    model: Type[AnyModelType],
    prefix: str,
    loc: Tuple[str, ...],
    case_reducer: Callable[[str], str],
) -> Iterator[Tuple[str, _FieldLocDescription]]:
    for field_name, field_type in _list_fields(model):
        upper_field_name = case_reducer(field_name)
        new_prefix = f'{prefix}_{upper_field_name}'
        new_loc = loc + (field_name,)
        is_complex, is_only_complex = _estimate_field_complexity(field_type)
        yield new_prefix, _FieldLocDescription(new_loc, is_complex, is_only_complex)
        if is_complex:
            yield from _traveler(
                cast(AnyModelType, field_type), new_prefix, new_loc, case_reducer
            )


def _build_model_flat_map(
    model: Type[BaseModel], prefix: str, case_reducer: Callable[[str], str]
) -> Dict[str, _FieldLocDescription]:
    return dict(_traveler(model, prefix, (), case_reducer))


class FlatMapValues(Dict[str, Json]):
    __slots__ = 'restored_env_values', 'restored_text_values'

    def __init__(
        self,
        restored_env_values: Dict[ModelLoc, str],
        restored_text_values: Dict[str, Union[TextValues, Dict]],
        **values: Json,
    ):
        super().__init__(**values)
        self.restored_env_values = restored_env_values
        self.restored_text_values = restored_text_values

    def get_location(self, val_loc: ModelLoc) -> FlatMapLoc:
        """
        Maps model location to flat-mapping location, preserving original case

        :param val_loc: model location
        :raises KeyError: in case if such value hasn't been restored
        :return: flat-mapping location
        """
        try:
            return self._get_location(val_loc)
        except KeyError:
            raise KeyError(val_loc)

    def _get_location(self, val_loc: ModelLoc) -> FlatMapLoc:
        try:
            return self.restored_env_values[val_loc], None
        except KeyError:
            pass

        loc_iter = iter(val_loc)

        key_used: Optional[str] = None
        text_vals: Optional[TextValues] = None

        curr = self.restored_text_values
        for part in loc_iter:
            curr = curr[part]
            if isinstance(curr, tuple):
                key_used, text_vals = curr
                break

        if text_vals is None:
            raise KeyError(val_loc)

        return key_used, text_vals.get_location(tuple(loc_iter))


class InvalidAssignError(ValueError):
    """
    Describes error occurrence and it location while applying some flat value
    """

    def __init__(self, loc: Optional[Sequence[str]], key: str):
        self.loc = loc
        self.key = key


class CannotParseValueError(InvalidAssignError):
    """Value provided by `key` expected to be parsable for `loc`"""

    pass


class AssignBeyondSimpleValueError(InvalidAssignError):
    """
    Signals that some value arrives for some deep location after a simple value for
    this location parent, e.g. that sequence of items
    :code:`[('FOO_BAR', 1), ('FOO_BAR_BAZ', 2')]` will cause
    `AssignBeyondSimpleValueError` error.
    """

    pass


class ModelShapeRestorer(object):
    """
    Restores flattened mapping to a model shape for a flat-map where keys satisfies
    that rule:

    .. code-block:: python

        def get_flat_map_key(prefix, loc):
            return prefix + '_' + '_'.join(str(part) for part in loc)

    Where `prefix` - some arbitrary prefix, mostly aimed to separate different
    namespaces, `loc` - a sequence of keys and indexes, by which desired value may be
    addressed inside model and her nested fields. Also there is possibility to make
    flat-map key case insensitive.

    Currently, setting nested a value inside of any sequence isn't supported.
    """

    def __init__(
        self,
        model: AnyModelType,
        prefix: str,
        case_sensitive: bool,
        dead_end_value_resolver: Callable[[str], TextValues],
    ):
        self._case_reducer = _noop if case_sensitive else str.casefold
        self._prefix = self._case_reducer(prefix)
        self._model_flat_map = _build_model_flat_map(
            model, self._prefix, self._case_reducer
        )
        self._dead_end_resolver = dead_end_value_resolver

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, val: str):
        self._prefix = val

    def restore(
        self, flat_map: Mapping[str, str]
    ) -> Tuple['FlatMapValues', Optional[Sequence[InvalidAssignError]]]:
        errs: List[InvalidAssignError] = []
        target: Dict[str, Json] = {}
        consumed_envs: Dict[ModelLoc, str] = {}

        def default_dict_factory():
            return defaultdict(default_dict_factory)

        consumed_text_vals = default_dict_factory()

        for orig_key, val in flat_map.items():
            key = self._case_reducer(orig_key)
            if not key.startswith(self._prefix):
                continue

            try:
                path, is_complex, is_only_complex = self._model_flat_map[key]
            except KeyError:
                continue

            if is_complex or is_only_complex:
                try:
                    val = self._dead_end_resolver(val)
                    assert isinstance(val, TextValues), 'Check is correct decoder used'
                    reduce(
                        lambda curr, item: curr[item], path[:-1], consumed_text_vals
                    )[path[-1]] = (orig_key, val)
                except ParsingError as err:
                    if is_only_complex:
                        new_err = CannotParseValueError(path, orig_key)
                        new_err.__cause__ = err.cause
                        errs.append(new_err)
                        continue

            try:
                _apply_path_value(target, path, orig_key, val)
            except InvalidAssignError as e:
                errs.append(e)
            else:
                consumed_envs[path] = orig_key

        return FlatMapValues(consumed_envs, consumed_text_vals, **target), errs


def _apply_path_value(
    root: JsonDict, path: Sequence[str], orig_key: str, value: Union[str, JsonDict]
):
    curr_segment: Any = root
    for path_part in path[:-1]:
        if not isinstance(curr_segment, dict):
            raise AssignBeyondSimpleValueError(path, orig_key)
        try:
            next_segment = curr_segment[path_part]
        except KeyError:
            next_segment = {}
            curr_segment[path_part] = next_segment

        curr_segment = next_segment
    curr_segment[path[-1]] = value
