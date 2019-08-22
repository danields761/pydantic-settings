from dataclasses import is_dataclass
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
)
from attr import has as is_attr_class
from pydantic import BaseModel

from pydantic_settings.types import JsonDict, AnyModelType, Json, ModelLocation


_RecStrDictValue = Union['_RecStrDict', str]
_RecStrDict = Dict[str, _RecStrDictValue]
_NestedMappingPath = Tuple[Sequence[str], bool, bool]


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
    if not hasattr(field_type, '__origin__') or field_type.__origin__ is not Union:
        return False, False

    return (
        True,
        all(
            not _is_determined_complex_field(subtype) for subtype in field_type.__args__
        ),
    )


def _list_fields(model: AnyModelType) -> Iterator[Tuple[str, Type]]:
    if issubclass(model, BaseModel):
        for field in model.__fields__.values():
            yield field.name, field.type_
    elif is_attr_class(model):
        for field in model.__attrs_attrs__:
            yield field.name, field.type
    elif is_dataclass(model):
        for field in model.__dataclass_fields__.values():
            yield field.name, field.type
    else:
        raise TypeError("value isn't a model type")


def _traveler(
    model: Type[AnyModelType],
    prefix: str,
    loc: Tuple[str, ...],
    case_reducer: Callable[[str], str],
) -> Iterator[Tuple[str, _NestedMappingPath]]:
    for field_name, field_type in _list_fields(model):
        upper_field_name = case_reducer(field_name)
        new_prefix = f'{prefix}_{upper_field_name}'
        new_loc = loc + (field_name,)
        is_complex, is_only_complex = _estimate_field_complexity(field_type)
        yield new_prefix, (new_loc, is_complex, is_only_complex)
        if is_complex:
            yield from _traveler(
                cast(AnyModelType, field_type), new_prefix, new_loc, case_reducer
            )


def _build_model_flat_map(
    model: Type[BaseModel], prefix: str, case_reducer: Callable[[str], str]
) -> Dict[str, _NestedMappingPath]:
    return dict(_traveler(model, prefix, (), case_reducer))


class FlatMapValues(Dict[str, Json]):
    __slots__ = 'restored_values', 'restore_errs'

    def __init__(self, restored_values: Dict[ModelLocation, str], **values: Json):
        super().__init__(**values)
        self.restored_values = restored_values

    def get_location(self, val_loc: ModelLocation) -> str:
        """
        Maps model location to flat-mapping location, preserving original case

        :param val_loc: model location
        :raises KeyError: in case if such value hasn't been restored
        :return: flat-mapping location
        """
        return self.restored_values[val_loc]


class InvalidAssignError(ValueError):
    """
    Describes error occurrence and it location while applying some flat value
    """

    def __init__(self, loc: Sequence[str], key: str):
        self.loc = loc
        self.key = key


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
        dead_end_value_resolver: Callable[[str], _RecStrDict],
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
        target: Dict[str, Json] = {}
        errs: List[InvalidAssignError] = []
        consumed: Dict[ModelLocation, str] = {}
        for orig_key, val in flat_map.items():
            key = self._case_reducer(orig_key)
            if not key.startswith(self._prefix):
                continue
            try:
                path, is_complex, is_only_complex = self._model_flat_map[key]
            except KeyError:
                continue
            try:
                self._apply_path_value(
                    target, path, is_complex, is_only_complex, orig_key, val
                )
            except InvalidAssignError as e:
                errs.append(e)
            else:
                consumed[tuple(path)] = orig_key

        return FlatMapValues(consumed, **target), errs

    def _apply_path_value(
        self,
        root: JsonDict,
        path: Sequence[str],
        is_complex: bool,
        is_only_complex: bool,
        orig_key: str,
        value: str,
    ):
        curr_segment: Any = root
        for path_part in path[:-1]:
            try:
                next_segment = curr_segment[path_part]
            except KeyError:
                next_segment = {}
                curr_segment[path_part] = next_segment

            if isinstance(next_segment, str):
                try:
                    next_segment = self._dead_end_resolver(curr_segment)
                except (ValueError, TypeError) as e:
                    raise AssignBeyondSimpleValueError(path, orig_key) from e
                curr_segment[path_part] = next_segment

            curr_segment = next_segment

        if is_complex:
            try:
                value = self._dead_end_resolver(value)
            except (ValueError, KeyError) as e:
                if is_only_complex:
                    raise InvalidAssignError(path, orig_key) from e
        curr_segment[path[-1]] = value
