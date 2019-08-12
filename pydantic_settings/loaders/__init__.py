from typing import Type, Callable, Optional

from attr import dataclass

from .common import (
    Location,
    Document,
    LocationFinder,
    KeyLookupError,
    ListExpectError,
    MappingExpectError,
    DocumentLoaderCallable,
)


def _get_json_loader():
    from .json import load_document
    from json import JSONDecodeError

    return LoaderMeta(
        'json',
        JSONDecodeError,
        load_document,
        lambda err: Location(err.lineno, err.colno, -1, -1),
    )


def _get_yaml_loader():
    from .yaml import load_document
    from yaml import YAMLError, MarkedYAMLError

    def get_err_location(err: Exception) -> Optional[Location]:
        if not isinstance(err, MarkedYAMLError):
            return None
        return Location(err.problem_mark.line + 1, err.problem_mark.column + 1, -1, -1)

    return LoaderMeta('yaml', YAMLError, load_document, get_err_location)


def _get_toml_loader():
    raise NotImplementedError('TOML loader still not implemented')


@dataclass
class LoaderMeta:
    name: str
    root_exc: Type[Exception]

    load: DocumentLoaderCallable
    get_err_loc: Callable[[Exception], Optional[Location]]


def get_loader(loader_type: str) -> LoaderMeta:
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
