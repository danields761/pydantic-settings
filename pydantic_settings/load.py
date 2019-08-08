"""
Some utilities to help with *pydantic* or extends it's behaviour
"""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Type, TextIO, Optional, List, Union, Tuple, Any

from attr import dataclass
from pydantic import BaseModel, ValidationError

from pydantic_settings.base import SettingsModel, ExtendedErrorWrapper
from pydantic_settings.loaders import (
    Document,
    DocumentLoader,
    get_loader,
    Location,
    KeyLookupError,
)
from pydantic_settings.utils import flatten_errors_wrappers


dataclass = partial(dataclass, repr=True, str=True)


@dataclass
class ConfigLoadError(ValueError):
    """
    Indicates that configuration file couldn't be loaded and provides cause of this error
    """

    file_path: Path
    msg: str = None

    @property
    def args(self) -> List[Any]:
        return list(self.__dict__.values())


@dataclass(kw_only=True)
class ConfigMultipleErrors(ConfigLoadError):
    file_path: Path
    errs: List[ConfigLoadError]

    @classmethod
    def ensure_multiple(cls, errs: List[ConfigLoadError]) -> ConfigLoadError:
        assert len(errs) > 0
        if len(errs) == 1:
            return errs[0]
        self = cls(file_path=errs[0].file_path, errs=errs)
        return self.with_traceback(errs[0].__traceback__)


@dataclass(kw_only=True)
class LoaderError(ConfigLoadError):
    file_path: Path
    loader_name: str
    err: Exception


@dataclass(kw_only=True)
class InvalidValueError(ConfigLoadError):
    file_path: Path
    loc: Union[Location, str, List[Union[str, int]]]
    err: Exception
    from_env: bool = False


def load_config(
    cls: Type[SettingsModel],
    file_or_path: Union[TextIO, str, Path],
    *,
    type_hint: str = None,
    load_env: bool = False
) -> BaseModel:
    """
    Load settings from file and/or environment variables and binds them to a *pydantic* model. Supports *json*,
    *yaml* and *toml* formats. File format is inferred from file extension or from given type hint.

    :param cls: model class
    :param file_or_path: configuration file name
    :param type_hint: type hint from which appropriate decoder may be chosen
    :param load_env: load environment variables
    :raises ConfigLoadError: in case if any error occurred while loading configuration file
    :return: settings model instance
    """
    # prepare list of loaders based on file such parameters
    # as file extension and given type hint
    try_loaders: List[str, DocumentLoader, Tuple[Exception]] = []

    if isinstance(file_or_path, (str, Path)):
        file_path = (
            file_or_path if isinstance(file_or_path, Path) else Path(file_or_path)
        )
    else:
        file_path = Path(file_or_path.name)

    file_last_suffix = file_path.suffix
    if file_last_suffix != '':
        try_loaders.append(get_loader(file_last_suffix))
    if type_hint is not None:
        l = get_loader(type_hint)
        if l not in try_loaders:
            try_loaders.append(l)

    if len(try_loaders) == 0:
        raise ConfigLoadError(file_path, 'unable to find appropriate loader')

    # try loaders until valid result will be returned
    document: Optional[Document] = None
    errors_while_trying: List[ConfigLoadError] = []
    for attempt, (loader_name, loader, loader_err_cls) in enumerate(try_loaders, 1):
        try:
            document = loader(file_or_path)
        except loader_err_cls as e:
            errors_while_trying.append(
                LoaderError(file_path=file_path, loader_name=loader_name, err=e)
            )
        except FileNotFoundError:
            errors_while_trying.append(ConfigLoadError(file_path=file_path, msg='file not found'))
        else:
            if isinstance(document.content, dict):
                break
            document = None
            errors_while_trying.append(
                LoaderError(
                    file_path=file_path,
                    loader_name=loader_name,
                    err=ValueError('value at root must be a dictionary'),
                )
            )

    assert document is not None or len(errors_while_trying) > 0
    if len(errors_while_trying) and document is None:
        raise ConfigMultipleErrors.ensure_multiple(errors_while_trying)

    # construct object
    errs: List[ConfigLoadError] = []
    try:
        if load_env:
            import os

            result = cls.from_env(os.environ, **document.content)
        else:
            result = cls(**document.content)
    except ValidationError as e:
        assert len(e.raw_errors) > 0
        for raw_err in flatten_errors_wrappers(e.raw_errors):
            if not isinstance(raw_err, ExtendedErrorWrapper):
                try:
                    loc = document.location_finder.lookup_key_loc(raw_err.loc)
                except KeyLookupError:
                    # i don't really know what to do with such errors
                    # theoretically they should be never raised
                    loc = raw_err.loc
                errs.append(
                    InvalidValueError(file_path=file_path, loc=loc, err=raw_err.exc)
                )
            else:
                errs.append(
                    InvalidValueError(
                        file_path=file_path,
                        loc=raw_err.env_loc,
                        err=raw_err.exc,
                        from_env=True,
                    )
                )

    if errs:
        raise ConfigMultipleErrors.ensure_multiple(errs)

    return result
