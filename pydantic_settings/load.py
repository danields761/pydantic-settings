from io import StringIO
from os import environ as os_environ
from pathlib import Path
from typing import Type, TextIO, Optional, List, Union, Mapping, Tuple

from pydantic import BaseModel, ValidationError

from pydantic_settings.base import BaseSettingsModel
from pydantic_settings.decoder import get_decoder, DecoderMeta, ParsingError
from pydantic_settings.errors import (
    LoadingError,
    LoadingValidationError,
    LoadingParseError,
    with_errs_locations,
)
from pydantic_settings.restorer import FlatMapValues
from pydantic_settings.utils import deep_merge_mappings


def _resolve_arguments(
    any_content: Union[TextIO, str, Path], type_hint: str = None
) -> Tuple[DecoderMeta, Optional[Path], str]:
    if isinstance(any_content, Path):
        file_path = Path(any_content)
        try:
            content = file_path.read_text()
        except FileNotFoundError as err:
            raise LoadingError(file_path, err)
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

    if type_hint is not None:
        try:
            return get_decoder(type_hint), file_path, content
        except TypeError:
            pass

    if file_path:
        file_extension = file_path.suffix
        if file_extension != '':
            try:
                return get_decoder(file_extension), file_path, content
            except TypeError:
                pass
    else:
        file_extension = None

    err_parts: List[str] = []
    if type_hint is not None:
        err_parts.append(f'type hint "{type_hint}"')
    if file_extension is not None:
        err_parts.append(f'file extension "{file_extension}"')

    if type_hint is None and file_extension is None:
        msg = (
            'unable to find suitable decoder because no hints provided: '
            'expecting either file extension or "type_hint" argument'
        )
    else:
        msg = f'unable to find suitable decoder, hints used: {", ".join(err_parts)}'

    raise LoadingError(file_path, msg=msg)


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
    is complex a bit: firstly, if `type_hint` is provided, this value is tried to
    find decoder, in case of failure, if file path is provided or content stream has
    :code:`name` attribute and file name have common extension ("yaml", "json" etc),
    appropriate decoder is used, otherwise exception is raised.

    :param cls: model class
    :param any_content: configuration file name as `Path` or text content as string or stream
    :param type_hint: type hint from which appropriate decoder may be chosen
    :param load_env: load environment variables
    :param _environ: semi-private parameter intended to easily mock environ from tests

    :raises LoadingError: in case if any error occurred while loading settings

    :return: settings model instance
    """
    decoder_desc, file_path, content = _resolve_arguments(any_content, type_hint)

    try:
        file_values = decoder_desc.values_loader(content)
    except ParsingError as err:
        raise LoadingParseError(
            file_path, err.cause, location=err.file_location, decoder=decoder_desc
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
