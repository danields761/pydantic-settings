"""
*yaml*, *json* and *toml* decoders which also able to locate some value inside text
or file
"""
from typing import Callable, Union, TextIO

from attr import dataclass

from .common import (
    LocationLookupError,
    ListExpectError,
    MappingExpectError,
    ParsingError,
    TextValues,
)


@dataclass
class DecoderMeta:
    """Decoder matadata"""

    name: str
    values_loader: Callable[[Union[str, TextIO]], TextValues]


def _get_json() -> DecoderMeta:
    from .json import decode_document

    return DecoderMeta('json', decode_document)


def _get_yaml() -> DecoderMeta:
    from .yaml import decode_document

    return DecoderMeta('yaml', decode_document)


def _get_toml() -> DecoderMeta:
    raise NotImplementedError('TOML decoder still not implemented')


class DecoderNotFoundError(TypeError):
    """Error for cases when requested decoder not found"""


class DecoderMissingRequirementError(DecoderNotFoundError):
    """Error for cases when requested decoder requirement is missing"""


def _guard_import_error(
    decoder_loader: Callable[[], DecoderMeta], decoder_type: str
) -> DecoderMeta:
    try:
        return decoder_loader()
    except ImportError as err:
        raise DecoderMissingRequirementError(
            f'''"{decoder_type}" doesn't supported because "{
                err.path
            }" isn't installed'''
        ) from err


def get_decoder(decoder_type: str) -> DecoderMeta:
    """
    Get decoder for given type-hint. Decoders imported in lazy-style, allowing
    you to mark *pyyaml* and *tomlkit* as optional dependencies.

    :param decoder_type: any kind of decoder hint: file extension, mime-type or common
        name
    :return: decoder metadata
    """
    # i'am not really sure about possibility to guess mime-type for something like json
    if decoder_type in ('json', '.json', 'application/json'):
        return _guard_import_error(_get_json, 'json')
    if decoder_type in (
        'yaml',
        'yml',
        '.yaml',
        '.yml',
        'text/x-yaml',
        'applicaiton/x-yaml',
        'text/yaml',
        'application/yaml',
    ):
        return _guard_import_error(_get_yaml, 'yaml')
    if decoder_type in ('.toml', 'toml', 'text/toml'):
        return _guard_import_error(_get_toml, 'toml')
    raise DecoderNotFoundError(f'Loader "{decoder_type}" isn\'t supported')
