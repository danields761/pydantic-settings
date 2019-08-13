"""
Some utilities to help with *pydantic* or extends it's behaviour
"""
from __future__ import annotations

from io import StringIO
from os import environ as os_environ
from pathlib import Path
from typing import Type, TextIO, Optional, List, Union, Mapping, Tuple

from pydantic import BaseModel, ValidationError
from pydantic.error_wrappers import ErrorWrapper

from pydantic_settings.base import BaseSettingsModel
from pydantic_settings.errors import (
    ExtendedErrorWrapper,
    flatten_errors_wrappers,
    LoadingError,
    LoadingValidationError,
    LoadingParseError,
)
from pydantic_settings.loaders import Document, get_loader, KeyLookupError, LoaderMeta


def _lookup_loader(
    file_or_path: Union[TextIO, str, Path], type_hint: str = None
) -> Tuple[List[LoaderMeta], Path, str]:
    try_loaders: List[LoaderMeta] = []

    if isinstance(file_or_path, Path):
        file_path = Path(file_or_path)
        content = file_path.read_text()
    else:
        if isinstance(file_or_path, StringIO):
            file_path = None
            content = file_or_path.getvalue()
        elif isinstance(file_or_path, str):
            content = file_or_path
            file_path = None
        else:
            file_path = Path(file_or_path.name)
            content = file_path.read_text()

    if file_path:
        file_last_suffix = file_path.suffix
        if file_last_suffix != '':
            try_loaders.append(get_loader(file_last_suffix))
    if type_hint is not None:
        type_hint_loader = get_loader(type_hint)
        if type_hint_loader not in try_loaders:
            try_loaders.append(type_hint_loader)

    if len(try_loaders) == 0:
        raise LoadingError(
            file_path, msg='unable to find appropriate loader for file of this type'
        )

    return try_loaders, file_path, content


def load_settings(
    cls: Type[BaseSettingsModel],
    file_or_path: Union[TextIO, str, Path],
    *,
    type_hint: str = None,
    load_env: bool = False,
    _environ: Mapping[str, str] = None,
) -> BaseModel:
    """
    Load settings from file and/or environment variables and binds them to a
    *pydantic* model. Supports *json*, *yaml* and *toml* formats. File format is
    inferred from file extension or from given type hint.

    :param cls: model class
    :param file_or_path: configuration file name
    :param type_hint: type hint from which appropriate decoder may be chosen
    :param load_env: load environment variables
    :param _environ: semi-private parameter intended to easily mock environ from tests

    :raises ConfigLoadError: in case if any error occurred while loading
    configuration file

    :return: settings model instance
    """
    # prepare list of loaders based on file such parameters
    # as file extension and given type hint
    try_loaders, file_path, content = _lookup_loader(file_or_path, type_hint)

    # try loaders until valid result will be returned
    document: Optional[Document] = None
    errors_while_trying: List[Exception] = []
    for attempt, loader_desc in enumerate(try_loaders, 1):
        try:
            document = loader_desc.load(content)
        except loader_desc.root_exc as e:
            errors_while_trying.append(
                LoadingParseError(
                    file_path,
                    e,
                    f'parsing exception occurs in loader of "{loader_desc.name}" type',
                    location=loader_desc.get_err_loc(e),
                    loader=loader_desc,
                )
            )
            continue
        except FileNotFoundError:
            raise LoadingError(file_path, msg='file not found')

        if document.content is not None and not isinstance(document.content, dict):
            errors_while_trying.append(
                LoadingError(file_path, msg='value at root must be a dictionary')
            )
        else:
            break

    assert document is not None or len(errors_while_trying) > 0
    if len(errors_while_trying) and document is None:
        raise LoadingError(
            file_path,
            msg='some loaders being tried, but all failed',
            errs=errors_while_trying,
        )

    # construct object
    document_content = document.content or {}
    try:
        if load_env:
            result = cls.from_env(_environ or os_environ, **document_content)
        else:
            result = cls(**document_content)
    except ValidationError as e:
        assert len(e.raw_errors) > 0

        errs: List[ErrorWrapper] = []
        for raw_err in flatten_errors_wrappers(e.raw_errors):
            if not isinstance(raw_err, ExtendedErrorWrapper):
                try:
                    loc = document.location_finder.lookup_key_loc(raw_err.loc)
                    raw_err = ExtendedErrorWrapper.from_error_wrapper(
                        raw_err, text_loc=loc
                    )
                except KeyLookupError:
                    # i not really sure what to do with such errors
                    # theoretically they should never happen
                    pass
            errs.append(raw_err)

        raise LoadingValidationError(errs, file_path, content) from e

    return result
