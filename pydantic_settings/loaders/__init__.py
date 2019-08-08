from typing import Tuple, Type

from .common import (
    Location,
    Document,
    LocationFinder,
    KeyLookupError,
    ListExpectError,
    MappingExpectError,
    DocumentLoader,
)


def _get_json_loader():
    from .json import load_document
    from json import JSONDecodeError

    return 'json', load_document, JSONDecodeError


def _get_yaml_loader():
    from .yaml import load_document
    from yaml import YAMLError

    return 'yaml', load_document, YAMLError


def _get_toml_loader():
    raise NotImplementedError('TOML loader still not implemented')


def get_loader(loader_type: str) -> Tuple[str, DocumentLoader, Type[Exception]]:
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
    raise ValueError(f"Loader {loader_type} isn't being supported")
