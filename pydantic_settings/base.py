from __future__ import annotations

from dataclasses import Field, is_dataclass
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterator,
    List,
    Tuple,
    Type,
    Union,
    cast,
    Mapping,
    Callable,
    Optional,
    TypeVar,
)

import toml
from attr import has as is_attr_class
from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper
from typing_extensions import Protocol

from pydantic_settings.utils import flatten_errors_wrappers


class _DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Field]]


class _AttrsProtocol(Protocol):
    __attrs_attrs__: ClassVar[Dict[str, Any]]


_AnyModelType = Type[Union[BaseModel, _DataclassProtocol, _AttrsProtocol]]
_RecStrDictValue = Union['_RecStrDict', str]
_RecStrDict = Dict[str, _RecStrDictValue]
_NestedMappingPath = Tuple[List[str], bool]


def _is_determined_complex_field(field_type: Any):
    return (
        is_attr_class(field_type)
        or is_dataclass(field_type)
        or (isinstance(field_type, type) and issubclass(field_type, BaseModel))
    )


def _list_fields(model: _AnyModelType) -> Iterator[Tuple[str, Type]]:
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
        raise TypeError("values isn't a model type")


def _traveler(
    model: Type[_AnyModelType],
    prefix: str,
    loc: List[str],
    case_reducer: Callable[[str], str],
) -> Iterator[Tuple[str, _NestedMappingPath]]:
    for field_name, field_type in _list_fields(model):
        upper_field_name = case_reducer(field_name)
        new_prefix = f'{prefix}_{upper_field_name}'
        new_loc = loc + [field_name]
        is_complex_field = _is_determined_complex_field(field_type)
        yield new_prefix, (new_loc, is_complex_field)
        if is_complex_field:
            yield from _traveler(
                cast(_AnyModelType, field_type), new_prefix, new_loc, case_reducer
            )


def _build_model_flat_map(
    model: Type[BaseModel], prefix: str, case_reducer: Callable[[str], str]
) -> Dict[str, _NestedMappingPath]:
    return dict(_traveler(model, prefix, [], case_reducer))


class FlatMapRestoreError(Exception):
    pass


class InvalidAssignError(ValueError, FlatMapRestoreError):
    pass


class AssignBeyondSimpleValueError(InvalidAssignError):
    pass


class FlatMapRestorer(object):
    """
    Restores flattened nested mapping, as example
    """

    def __init__(
        self,
        model: _AnyModelType,
        prefix: str,
        case_sensitive: bool,
        dead_end_value_resolver: Callable[[str], _RecStrDict],
    ):
        self._case_reducer = str.casefold if case_sensitive else lambda v: v
        self._prefix = self._case_reducer(prefix)
        self._model_flat_map = _build_model_flat_map(
            model, self._prefix, self._case_reducer
        )
        self._dead_end_resolver = dead_end_value_resolver

    def apply_values(self, target: Any, flat_map: Mapping[str, str]) -> Dict[str, str]:
        consumed: Dict[Tuple[str, ...], str] = {}
        for orig_key, val in flat_map.items():
            key = self._case_reducer(orig_key)
            if not key.startswith(self._prefix):
                continue
            try:
                path, is_complex = self._model_flat_map[key]
            except KeyError:
                continue
            self._apply_path_value(target, path, is_complex, val)
            consumed[tuple(path)] = orig_key

        return consumed

    @staticmethod
    def _get_getter_setter(
        obj: Any
    ) -> Tuple[Callable[[Any, str, Any], None], Callable[[Any, str], Any]]:
        if hasattr(obj, '__setitem__') and hasattr(obj, '__getitem__'):
            return type(obj).__setitem__, type(obj).__getitem__
        else:
            return setattr, getattr

    def _apply_path_value(
        self, root: Any, path: List[str], is_complex: bool, value: str
    ):
        curr_segment: Any = root
        for path_part in path[:-1]:
            setter, getter = self._get_getter_setter(curr_segment)

            try:
                new_segment = getter(curr_segment, path_part)
            except KeyError:
                new_segment = {}
                setter(curr_segment, path_part, new_segment)

            if isinstance(new_segment, str):
                try:
                    new_segment = self._dead_end_resolver(curr_segment)
                    setter(curr_segment, path_part, new_segment)
                except (ValueError, TypeError) as e:
                    raise InvalidAssignError(e)

            curr_segment = new_segment

        if is_complex:
            try:
                value = self._dead_end_resolver(value)
            except (ValueError, KeyError):
                pass
        setter, _ = self._get_getter_setter(curr_segment)
        setter(curr_segment, path[-1], value)


T = TypeVar('T', bound='SettingsModel')


class ExtendedErrorWrapper(ErrorWrapper):
    __slots__ = ('env_loc',)

    def __init__(self, *args: Any, env_loc: str = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.env_loc = env_loc

    @classmethod
    def from_error_wrapper(
        cls, err_wrapper: ErrorWrapper, env_loc: str
    ) -> ExtendedErrorWrapper:
        ext_wrappper = object.__new__(cls)
        for attr in err_wrapper.__slots__:
            setattr(ext_wrappper, attr, getattr(err_wrapper, attr))
        ext_wrappper.env_loc = env_loc
        return ext_wrappper

    def dict(self, *, loc_prefix: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
        d = super().dict(loc_prefix=loc_prefix)
        d['env_loc'] = self.env_loc
        return d


class SettingsModel(BaseModel):
    class Config:
        env_prefix: ClassVar[str] = 'APP'
        complex_inline_values_decoder = toml.loads

    _FLAT_NAMES_MAPPER_MAP: ClassVar[Dict[str, List[str]]] = {}

    def __init_subclass__(cls, **kwargs):
        config = cast(cls.Config, cls.__config__)
        cls._restorer = FlatMapRestorer(
            cls, config.env_prefix, True, config.complex_inline_values_decoder
        )

    @classmethod
    def from_env(cls: Type[T], environ: Mapping[str, str], **vals: Any) -> T:
        env_vars_applied = cls._restorer.apply_values(vals, environ)
        try:
            return cls(**vals)
        except ValidationError as e:
            new_raw_errs: List[ErrorWrapper] = []
            for raw_err in flatten_errors_wrappers(e.raw_errors):
                try:
                    new_raw_errs.append(
                        ExtendedErrorWrapper.from_error_wrapper(raw_err, env_vars_applied[raw_err.loc])
                    )
                except KeyError:
                    new_raw_errs.append(raw_err)
            e.raw_errors = new_raw_errs
            raise e

    def with_env(self: T, environ: Mapping[str, str]) -> T:
        return self.from_env(environ, self.dict())
