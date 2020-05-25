import json
from io import StringIO
from os import environ as os_environ
from pathlib import Path
from typing import Type, TextIO, Optional, Union, Mapping, Tuple, TypeVar, Callable

from pydantic import BaseModel, ValidationError

from pydantic_settings.base import BaseSettingsModel
from pydantic_settings.decoder import (
    get_decoder,
    DecoderMeta,
    ParsingError,
    TextValues,
    DecoderNotFoundError,
)
from pydantic_settings.errors import (
    LoadingError,
    LoadingValidationError,
    LoadingParseError,
    with_errs_locations,
)
from pydantic_settings.restorer import FlatMapValues, ModelShapeRestorer
from pydantic_settings.types import JsonDict
from pydantic_settings.utils import deep_merge_mappings


def _resolve_content_arg(
    any_content: Union[TextIO, str, Path],
    type_hint: str,
    content_reader: Callable[[Path], str],
) -> Tuple[DecoderMeta, Optional[Path], str]:
    def decoder_by_type_hint(file_path_: Path = None) -> DecoderMeta:
        try:
            return get_decoder(type_hint)
        except DecoderNotFoundError as err_:
            raise LoadingError(file_path_, err_)

    if isinstance(any_content, Path):
        file_path = any_content
        try:
            content = content_reader(file_path)
        except FileNotFoundError as err:
            raise LoadingError(file_path, err)

        try:
            return get_decoder(file_path.suffix), file_path, content
        except DecoderNotFoundError as err:
            if type_hint is None:
                raise LoadingError(
                    file_path,
                    err,
                    f'cannot determine decoder from file suffix "{file_path.suffix}"',
                )

            return decoder_by_type_hint(file_path), file_path, content
    else:
        if isinstance(any_content, StringIO):
            content = any_content.getvalue()
        elif isinstance(any_content, str):
            content = any_content
        else:
            content = any_content.read()

        if type_hint is None:
            raise LoadingError(
                None,
                None,
                f'"type_hint" argument is required if '
                f'content is not an instance of "{Path.__module__}.'
                f'{Path.__qualname__}" class',
            )

        return decoder_by_type_hint(), None, content


def _get_shape_restorer(cls: Type[BaseModel], env_prefix: str) -> ModelShapeRestorer:
    if issubclass(cls, BaseSettingsModel):
        restorer = cls.shape_restorer
    else:
        restorer = ModelShapeRestorer(cls, env_prefix, False, json.loads)

    return restorer


SettingsM = TypeVar('SettingsM', bound=BaseModel)


def load_settings(
    cls: Type[SettingsM],
    any_content: Union[None, TextIO, str, Path] = None,
    *,
    type_hint: str = None,
    load_env: bool = False,
    env_prefix: str = 'APP',
    environ: Mapping[str, str] = None,
    _content_reader: Callable[[Path], str] = Path.read_text,
) -> SettingsM:
    """
    Load setting from provided content and merge with environment variables.
    Content may be loaded from file path, from file-like source or from plain text.

    If there is requirement to load settings only from environment variables, then
    `content` argument may be omitted.

    :param cls: either :py:class:`BaseSettingsModel` or :py:class:`pydantic.BaseModel`
        subclass type. The result will be instance of a given type.
    :param any_content: content from which settings will be loaded
    :param type_hint: determines content decoder. Required, if content isn't provided
        as a file path (e.g. content isn't instance of `pathlib.Path`). Takes
        precedence over actual file suffix.
    :param load_env: determines whether load environment variables or not
    :param env_prefix: determines prefix used to match model field with appropriate
        environment variable. *NOTE* if `cls` argument is subclass of
        :py:class:`BaseSettingsModel` then `env_prefix` argument will be ignored.
    :param environ: environment variables mapping, in case if this argument is `None`
        `os.environ` will be used

    :raises LoadingError: in case if any error occurred while loading settings

    :return: instance of settings model, provided by `cls` argument
    """
    if any_content is None and not load_env:
        raise LoadingError(None, msg='no sources provided to load settings from')

    decoder_desc: Optional[DecoderMeta] = None
    file_path: Optional[Path] = None
    content: Optional[str] = None

    if any_content is not None:
        decoder_desc, file_path, content = _resolve_content_arg(
            any_content, type_hint, _content_reader
        )

    document_content: Optional[JsonDict] = None
    file_values: Optional[TextValues] = None
    if content is not None:
        try:
            document_content = file_values = decoder_desc.values_loader(content)
        except ParsingError as err:
            raise LoadingParseError(
                file_path, err.cause, location=err.text_location, decoder=decoder_desc
            )

    # prepare environment values
    env_values: Optional[FlatMapValues] = None
    if load_env:
        # TODO: ignore env vars restoration errors so far
        restorer = _get_shape_restorer(cls, env_prefix)
        env_values, _ = restorer.restore(environ or os_environ)

        if document_content is not None:
            document_content = deep_merge_mappings(env_values, document_content)
        else:
            document_content = env_values

    try:
        result = cls(**document_content)
    except ValidationError as err:
        assert len(err.raw_errors) > 0
        new_err = err

        if file_values is not None:
            new_err = with_errs_locations(cls, err, file_values)
        if env_values is not None:
            new_err = with_errs_locations(cls, new_err, env_values)

        raise LoadingValidationError(new_err.raw_errors, cls, file_path) from err

    return result
