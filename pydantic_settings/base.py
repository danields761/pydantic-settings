from __future__ import annotations

from dataclasses import is_dataclass
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
    TypeVar,
    Sequence,
    Optional,
)

import toml
from attr import has as is_attr_class
from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper

from pydantic_settings.errors import ExtendedErrorWrapper, flatten_errors_wrappers
from pydantic_settings.attrs_docs import apply_attributes_docs
from pydantic_settings.types import AnyModelType


_RecStrDictValue = Union['_RecStrDict', str]
_RecStrDict = Dict[str, _RecStrDictValue]
_NestedMappingPath = Tuple[Sequence[str], bool]


def _is_determined_complex_field(field_type: Any):
    return (
        is_attr_class(field_type)
        or is_dataclass(field_type)
        or (isinstance(field_type, type) and issubclass(field_type, BaseModel))
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
        raise TypeError("values isn't a model type")


def _traveler(
    model: Type[AnyModelType],
    prefix: str,
    loc: Tuple[str],
    case_reducer: Callable[[str], str],
) -> Iterator[Tuple[str, _NestedMappingPath]]:
    for field_name, field_type in _list_fields(model):
        upper_field_name = case_reducer(field_name)
        new_prefix = f'{prefix}_{upper_field_name}'
        new_loc = loc + (field_name,)
        is_complex_field = _is_determined_complex_field(field_type)
        yield new_prefix, (new_loc, is_complex_field)
        if is_complex_field:
            yield from _traveler(
                cast(AnyModelType, field_type), new_prefix, new_loc, case_reducer
            )


def _build_model_flat_map(
    model: Type[BaseModel], prefix: str, case_reducer: Callable[[str], str]
) -> Dict[str, _NestedMappingPath]:
    return dict(_traveler(model, prefix, (), case_reducer))


class InvalidAssignError(ValueError):
    def __init__(self, loc: Sequence[str], key: str):
        self.loc = loc
        self.key = key


class AssignBeyondSimpleValueError(InvalidAssignError):
    pass


class FlatMapRestorer(object):
    """
    Restores flattened nested mapping, as example
    """

    def __init__(
        self,
        model: AnyModelType,
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

    def apply_values(
        self, target: Any, flat_map: Mapping[str, str]
    ) -> Tuple[Dict[Sequence[str], str], Sequence[InvalidAssignError]]:
        errs: List[InvalidAssignError] = []
        consumed: Dict[Sequence[str], str] = {}
        for orig_key, val in flat_map.items():
            key = self._case_reducer(orig_key)
            if not key.startswith(self._prefix):
                continue
            try:
                path, is_complex = self._model_flat_map[key]
            except KeyError:
                continue
            try:
                self._apply_path_value(target, path, is_complex, orig_key, val)
            except InvalidAssignError as e:
                errs.append(e)
            else:
                consumed[tuple(path)] = orig_key

        return consumed, errs

    @staticmethod
    def _get_getter_setter(
        obj: Any
    ) -> Tuple[Callable[[Any, str, Any], None], Callable[[Any, str], Any]]:
        if hasattr(obj, '__setitem__') and hasattr(obj, '__getitem__'):
            return type(obj).__setitem__, type(obj).__getitem__
        else:
            return setattr, getattr

    def _apply_path_value(
        self,
        root: Any,
        path: Sequence[str],
        is_complex: bool,
        orig_key: str,
        value: str,
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
                    # that mechanism should be reworked, because target field may decode
                    # string values by itself
                    raise InvalidAssignError(path, orig_key) from e

            curr_segment = new_segment

        if is_complex:
            try:
                value = self._dead_end_resolver(value)
            except (ValueError, KeyError) as e:
                raise InvalidAssignError(path, orig_key) from e
        setter, _ = self._get_getter_setter(curr_segment)
        setter(curr_segment, path[-1], value)


T = TypeVar('T', bound='SettingsModel')


class BaseSettingsModel(BaseModel):
    class Config:
        env_prefix: ClassVar[str] = 'APP'
        complex_inline_values_decoder = toml.loads
        build_attr_docs: bool = True
        override_exited_attrs_docs: bool = False

    _FLAT_NAMES_MAPPER_MAP: ClassVar[Dict[str, Sequence[str]]] = {}

    def __init_subclass__(cls, **kwargs):
        config = cast(cls.Config, cls.__config__)
        cls._restorer = FlatMapRestorer(
            cls, config.env_prefix, True, config.complex_inline_values_decoder
        )
        if config.build_attr_docs:
            apply_attributes_docs(
                cls, override_existed=config.override_exited_attrs_docs
            )

    @classmethod
    def from_env(cls: Type[T], environ: Mapping[str, str], **vals: Any) -> T:
        env_vars_applied, env_apply_errs = cls._restorer.apply_values(vals, environ)
        try:
            res = cls(**vals)
        except ValidationError as e:
            validation_err = e
        else:
            validation_err = None

        if env_apply_errs or validation_err:
            raise cls._combine_errors(env_apply_errs, validation_err, env_vars_applied)

        return res

    def with_env(self, environ: Mapping[str, str]):
        return self.from_env(environ, **self.dict())

    @staticmethod
    def _combine_errors(
        env_apply_errs: Sequence[InvalidAssignError],
        validation_err: Optional[ValidationError],
        env_vars_applied: Dict[Sequence[str], str],
    ) -> Optional[ValidationError]:
        err_wrappers: List[ErrorWrapper] = [
            ExtendedErrorWrapper(
                env_err.__cause__, loc=tuple(env_err.loc), env_loc=env_err.key
            )
            for env_err in env_apply_errs
        ]
        if validation_err is not None:
            err_wrappers += [
                ExtendedErrorWrapper.from_error_wrapper(raw_err, env_loc=err_env_loc)
                if err_env_loc is not None
                else raw_err
                for raw_err, err_env_loc in (
                    (raw_err, env_vars_applied.get(raw_err.loc))
                    for raw_err in flatten_errors_wrappers(validation_err.raw_errors)
                )
            ]
        if len(err_wrappers) == 0:
            return None

        return ValidationError(err_wrappers)
