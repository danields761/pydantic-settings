"""
Some utilities to help with *pydantic* or extends it's behaviour
"""
from __future__ import annotations

from functools import wraps
from json import load as jload, JSONDecodeError
from logging import getLogger
from os import path
from typing import Type, TypeVar, Callable, TextIO, Any, Dict, cast, Optional

from pydantic import BaseModel, BaseSettings, Extra
from yaml import load as yload, SafeLoader, YAMLError
from toml import loads as tloads, TomlDecodeError

from .types import Json, JsonDict


log = getLogger(__name__)


class ConfigLoadError(ValueError):
    """
    Indicates that configuration file couldn't be loaded and provides cause of this error
    """

    @property
    def cause(self) -> Optional[Exception]:
        if len(self.args) == 0 or not isinstance(self.args[0], Exception):
            return self
        return cast(Exception, self.args[0])


class _InternalParseError(Exception):
    @property
    def cause(self):
        return self.args[0]


def _change_exception(func, from_err_cls, to_err_cls):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except from_err_cls as err:
            raise to_err_cls(err)

    return wrapper


def _yaml_loader(f: TextIO) -> Json:
    return yload(f, SafeLoader)


_DECODERS = {
    'json': _change_exception(jload, JSONDecodeError, _InternalParseError),
    'yaml': _change_exception(_yaml_loader, YAMLError, _InternalParseError),
    'yml': _change_exception(_yaml_loader, YAMLError, _InternalParseError),
    'toml': _change_exception(
        lambda f: tloads(f.read()), TomlDecodeError, _InternalParseError
    ),
}


def load_config(
    cls: Type[BaseModel],
    file_name: str,
    *,
    type_hint: str = None,
    load_env: bool = False
) -> BaseModel:
    """
    Load configuration from file and/or environment variables and binds them to a *pydantic* model. Supports *json*,
    *yaml* and *toml* formats. File format is inferred from file extension or from given type hint.

    :param cls: model class
    :param file_name: configuration file name
    :param type_hint: type hint from which appropriate decoder may be chosen
    :param load_env: load environment variables
    :raises ConfigLoadError: in case if error occurred while loading configuration file
    :raises pydantic.ValidationError: in case if error occurred while mapping configuration values
    :return: configuration model instance
    """

    def load_and_parse(file: str, d: Callable[[TextIO], Json]) -> JsonDict:
        with open(file, 'rt') as f:
            try:
                decoded = d(f)
            except _InternalParseError as e:
                raise ConfigLoadError(e.cause)

            if not isinstance(decoded, dict):
                raise ConfigLoadError(
                    'wrong configuration file {}: expecting dictionary at root'.format(
                        file
                    )
                )

            return decoded

    def construct(values: Dict[Any, Any]) -> BaseModel:
        return cls(_load_env_variables=load_env, **values)

    file_suffix = path.split(file_name)[1]
    assert file_suffix
    use_type_hint = type_hint is not None and file_suffix != type_hint

    decoder, decoder_name = next(
        (
            (decoder, suffix)
            for suffix, decoder in _DECODERS.items()
            if file_suffix.endswith(suffix)
        ),
        _yaml_loader,
    )

    try:
        return construct(load_and_parse(file_name, decoder))
    except ConfigLoadError:
        if not use_type_hint or decoder_name == type_hint:
            raise

    new_decoder = next(
        (
            new_decoder
            for suffix, new_decoder in _DECODERS.items()
            if new_decoder is not decoder and type_hint.endswith(suffix)
        ),
        None,
    )
    if new_decoder is None:
        raise ConfigLoadError(
            "can't find appropriate decoder for file {} "
            "(also failed with additional type hint {})".format(file_name, type_hint)
        )

    return construct(load_and_parse(file_name, decoder))
