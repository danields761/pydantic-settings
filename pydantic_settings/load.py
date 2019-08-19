"""
Some utilities to help with *pydantic* or extends it's behaviour
"""
from io import StringIO
from os import environ as os_environ
from pathlib import Path
from typing import Type, TextIO, Optional, List, Union, Mapping, Tuple

from pydantic import BaseModel, ValidationError

from pydantic_settings.base import BaseSettingsModel
from pydantic_settings.errors import (
    LoadingError,
    LoadingValidationError,
    LoadingParseError,
    with_errs_locations,
)
from pydantic_settings.loaders import get_loader, LoaderMeta, ParsingError, FileValues
from pydantic_settings.types import Json, FlatMapValues
from pydantic_settings.utils import deep_merge_mappings


def _lookup_loaders(
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
    try_loaders, file_path, content = _lookup_loaders(file_or_path, type_hint)

    # try loaders until valid result will be returned
    file_values: Optional[FileValues] = None
    errors_while_trying: List[Exception] = []
    for attempt, loader_desc in enumerate(try_loaders, 1):
        try:
            file_values = loader_desc.values_loader(content)
            break
        except ParsingError as err:
            errors_while_trying.append(
                LoadingParseError(
                    file_path,
                    err.cause,
                    f'parsing exception occurs in loader of "{loader_desc.name}" type',
                    location=err.file_location,
                    loader=loader_desc,
                )
            )
            continue

    assert file_values is not None or len(errors_while_trying) > 0
    if len(errors_while_trying) and file_values is None:
        raise LoadingError(
            file_path,
            msg='some loaders being tried, but all failed',
            errs=errors_while_trying,
        )

    # construct object
    document_content = file_values

    # prepare environment values
    env_values: Optional[FlatMapValues] = None
    if load_env:
        # TODO: ignore env vars restoration errors so far
        env_values, _ = cls.shape_restorer.restore(_environ or os_environ)
        document_content = deep_merge_mappings(document_content, env_values)

    try:
        result = cls(**document_content)
    except ValidationError as err:
        assert len(err.raw_errors) > 0

        new_err = with_errs_locations(err, file_values)
        if env_values is not None:
            new_err = with_errs_locations(new_err, env_values)

        raise LoadingValidationError(new_err.raw_errors, file_path, content) from err

    return result
