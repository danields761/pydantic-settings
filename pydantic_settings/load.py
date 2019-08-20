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
from pydantic_settings.model_shape_restorer import FlatMapValues
from pydantic_settings.utils import deep_merge_mappings


def _resolve_arguments(
    any_content: Union[TextIO, str, Path], type_hint: str = None
) -> Tuple[LoaderMeta, Optional[Path], str]:
    if isinstance(any_content, Path):
        file_path = Path(any_content)
        try:
            content = file_path.read_text()
        except FileNotFoundError as err:
            raise LoadingError(file_path, err, msg='file not found')
    else:
        if isinstance(any_content, StringIO):
            file_path = None
            content = any_content.getvalue()
        elif isinstance(any_content, str):
            content = any_content
            file_path = None
        else:
            file_path = Path(any_content.name)
            content = any_content.read()

    if file_path:
        file_extension = file_path.suffix
        if file_extension != '':
            try:
                return get_loader(file_extension), file_path, content
            except TypeError:
                pass
    else:
        file_extension = None

    if type_hint is not None:
        try:
            return get_loader(type_hint), file_path, content
        except TypeError:
            pass

    err_parts: List[str] = []
    if file_extension is not None:
        err_parts.append(f'file extension "{file_extension}"')
    if type_hint is not None:
        err_parts.append(f'type hint "{type_hint}"')

    raise LoadingError(
        file_path,
        msg=f'unable to find suitable loader, hints used: {", ".join(err_parts)}',
    )


def load_settings(
    cls: Type[BaseSettingsModel],
    any_content: Union[TextIO, str, Path],
    *,
    type_hint: str = None,
    load_env: bool = False,
    _environ: Mapping[str, str] = None,
) -> BaseModel:
    """
    Load settings from file and/or environment variables and binds them to a
    *pydantic* model. Supports *json*, *yaml* and *toml* formats. File format choose
    is complex a bit: firstly, if file path provided or content stream has
    :code:`name` attribute and file name have common extension ("yaml", "json" etc),
    appropriate loader will be used, otherwise `type_hint` will be used.

    :param cls: model class
    :param any_content: configuration file name as `Path` or text content as string or
    stream
    :param type_hint: type hint from which appropriate decoder may be chosen
    :param load_env: load environment variables
    :param _environ: semi-private parameter intended to easily mock environ from tests

    :raises LoadingError: in case if any error occurred while loading
    configuration file

    :return: settings model instance
    """
    loader_desc, file_path, content = _resolve_arguments(any_content, type_hint)

    try:
        file_values = loader_desc.values_loader(content)
    except ParsingError as err:
        raise LoadingParseError(
            file_path,
            err.cause,
            f'parsing exception occurs in loader of "{loader_desc.name}" type',
            location=err.file_location,
            loader=loader_desc,
        )

    # construct object
    document_content = file_values

    # prepare environment values
    env_values: Optional[FlatMapValues] = None
    if load_env:
        # TODO: ignore env vars restoration errors so far
        env_values, _ = cls.shape_restorer.restore(_environ or os_environ)
        document_content = deep_merge_mappings(env_values, document_content)

    try:
        result = cls(**document_content)
    except ValidationError as err:
        assert len(err.raw_errors) > 0

        new_err = with_errs_locations(err, file_values)
        if env_values is not None:
            new_err = with_errs_locations(new_err, env_values)

        raise LoadingValidationError(new_err.raw_errors, file_path, content) from err

    return result
