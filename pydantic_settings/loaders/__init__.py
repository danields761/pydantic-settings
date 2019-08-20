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


def _get_json_loader():
    from .json import load_document

    return LoaderMeta('json', load_document)


def _get_yaml_loader():
    from .yaml import load_document

    return LoaderMeta('yaml', load_document)


def _get_toml_loader():
    raise NotImplementedError('TOML loader still not implemented')


@dataclass
class LoaderMeta:
    """Loader matadata"""

    name: str
    values_loader: Callable[[Union[str, TextIO]], FileValues]


def get_loader(loader_type: str) -> LoaderMeta:
    """
    Get loader for given type-hint. Loaders imported in lazy-style, allowing
    you to mark *pyyaml* and *tomlkit* as optional dependencies.

    :param loader_type: any kind of loader hint: file extension, mime-type or common
    name
    :return: loader metadata
    """
    # i'am not really sure about possibility to guess mime-type for something like json
    if loader_type in ('json', '.json', 'application/json'):
        return _get_json_loader()
    if loader_type in (
        'yaml',
        'yml',
        '.yaml',
        '.yml',
        'text/x-yaml',
        'applicaiton/x-yaml',
        'test/yaml',
        'application/yaml',
    ):
        return _get_yaml_loader()
    if loader_type in ('.toml', 'toml', 'text/toml'):
        return _get_toml_loader()
    raise ValueError(f"Loader {loader_type} isn't supported")
