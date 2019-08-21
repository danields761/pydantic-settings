"""
*yaml*, *json* and *toml* decoders which also able to locate some value inside text
or file
"""
from typing import Callable, Union, TextIO

from attr import dataclass

from .common import (
    FileLocation,
    LocationLookupError,
    ListExpectError,
    MappingExpectError,
    ParsingError,
    FileValues,
)


def _get_json():
    from .json import decode_document

    return DecoderMeta('json', decode_document)


def _get_yaml():
    from .yaml import decode_document

    return DecoderMeta('yaml', decode_document)


def _get_toml():
    raise NotImplementedError('TOML decoder still not implemented')


@dataclass
class DecoderMeta:
    """Decoder matadata"""

    name: str
    values_loader: Callable[[Union[str, TextIO]], FileValues]


def get_decoder(decoder_type: str) -> DecoderMeta:
    """
    Get decoder for given type-hint. Decoders imported in lazy-style, allowing
    you to mark *pyyaml* and *tomlkit* as optional dependencies.

    :param decoder_type: any kind of decoder hint: file extension, mime-type or common name
    :return: decoder metadata
    """
    # i'am not really sure about possibility to guess mime-type for something like json
    if decoder_type in ('json', '.json', 'application/json'):
        return _get_json()
    if decoder_type in (
        'yaml',
        'yml',
        '.yaml',
        '.yml',
        'text/x-yaml',
        'applicaiton/x-yaml',
        'test/yaml',
        'application/yaml',
    ):
        return _get_yaml()
    if decoder_type in ('.toml', 'toml', 'text/toml'):
        return _get_toml()
    raise TypeError(f"Loader {decoder_type} isn't supported")
