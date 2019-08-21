import tempfile
from io import StringIO
from pathlib import Path
from typing import List

from pydantic import IntegerError, FloatError, StrError
from pytest import mark, raises

from pydantic_settings import (
    BaseSettingsModel,
    LoadingError,
    load_settings,
    FileLocation,
    LoadingValidationError,
)


class Settings(BaseSettingsModel):
    class Config:
        env_prefix = 'T'

    foo: int
    bar: float


class Settings2(BaseSettingsModel):
    class Config:
        env_prefix = 'A'

    settings_list: List[Settings]
    settings: Settings
    foo: str = ''


@mark.parametrize(
    'model_cls, content, environ, locations',
    [
        (Settings, '{"bar": 1234}', {'T_FOO': 'AKA INT'}, [('T_FOO', IntegerError)]),
        (Settings, '{"bar": 1234}', {'T_foo': 'AKA INT'}, [('T_foo', IntegerError)]),
        (
            Settings,
            '{"bar": "AKA FLOAT"}',
            {'T_foo': 101},
            [(FileLocation(1, 9, 1, 20, 9, 19), FloatError)],
        ),
        (
            Settings2,
            '{}',
            {'A_SETTINGS_FOO': 'INVALID INT', 'A_SETTINGS_BAR': 1243},
            [('A_SETTINGS_FOO', IntegerError)],
        ),
        (
            Settings2,
            '{"settings_list": [], "settings": {"foo": 100, "bar": "INVALID FLOAT"}, "foo": []}',
            {},
            [
                (FileLocation(1, 55, 1, 70, 55, 69), FloatError),
                (FileLocation(1, 80, 1, 82, 80, 81), StrError),
            ],
        ),
        (
            Settings2,
            '{"settings_list": [], "settings": {"foo": 100}, "foo": []}',
            {'A_SETTINGS_BAR': 'INVALID FLOAT'},
            [
                ('A_SETTINGS_BAR', FloatError),
                (FileLocation(1, 56, 1, 58, 56, 57), StrError),
            ],
        ),
    ],
)
def test_validation_errors(model_cls, content, environ, locations):
    with raises(LoadingError) as exc_info:
        load_settings(
            model_cls, content, type_hint='json', load_env=True, _environ=environ
        )

    assert exc_info.type is LoadingValidationError
    assert [loc for loc, _ in exc_info.value.per_location_errors()] == [
        loc for loc, _ in locations
    ]
    assert [type(err) for _, err in exc_info.value.per_location_errors()] == [
        err_cls for _, err_cls in locations
    ]


def empty_tmp_file_creator(extension):
    def create():
        p = Path(tempfile.mktemp('.' + extension))
        p.touch()
        return p

    return create


@mark.parametrize(
    'any_content, type_hint, expect_err_msg',
    [
        (
            empty_tmp_file_creator('cfg'),
            None,
            'unable to find suitable decoder, hints used: file extension ".cfg"',
        ),
        ('', 'ini', 'unable to find suitable decoder, hints used: type hint "ini"'),
        (
            StringIO(''),
            'ini',
            'unable to find suitable decoder, hints used: type hint "ini"',
        ),
        (
            StringIO(''),
            None,
            'unable to find suitable decoder because no hints provided: '
            + 'expecting either file extension or "type_hint" argument',
        ),
        (
            empty_tmp_file_creator('cfg'),
            'DEFINITELY NOT A TYPE HINT',
            'unable to find suitable decoder, hints used: type hint "DEFINITELY NOT A TYPE HINT", file extension ".cfg"',
        ),
    ],
)
def test_loader_lookup_errors(any_content, type_hint, expect_err_msg):
    if callable(any_content):
        any_content = any_content()

    with raises(LoadingError) as err_info:
        load_settings(Settings2, any_content, type_hint=type_hint)

    assert err_info.value.msg == expect_err_msg


def test_file_not_found():
    path = Path(tempfile.mktemp())
    with raises(LoadingError) as err_info:
        load_settings(Settings2, path)

    assert isinstance(err_info.value.cause, FileNotFoundError)
    assert err_info.value.content is None
    assert err_info.value.file_path == path
