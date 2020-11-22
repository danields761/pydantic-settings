import tempfile
from io import StringIO
from pathlib import Path
from typing import List

from pydantic import FloatError, IntegerError, StrError
from pytest import mark, raises

from pydantic_settings import (
    BaseSettingsModel,
    LoadingError,
    LoadingValidationError,
    TextLocation,
    load_settings,
)
from pydantic_settings.errors import ExtendedErrorWrapper


def per_location_errors(load_err):
    return (
        (raw_err.source_loc, raw_err.exc)
        for raw_err in load_err.raw_errors
        if isinstance(raw_err, ExtendedErrorWrapper)
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
        (
            Settings,
            '{"bar": 1234}',
            {'T_FOO': 'AKA INT'},
            [(('T_FOO', None), IntegerError)],
        ),
        (
            Settings,
            '{"bar": 1234}',
            {'T_foo': 'AKA INT'},
            [(('T_foo', None), IntegerError)],
        ),
        (
            Settings,
            '{"bar": "AKA FLOAT"}',
            {'T_foo': 101},
            [(TextLocation(1, 9, 1, 20, 9, 19), FloatError)],
        ),
        (
            Settings2,
            '{}',
            {'A_SETTINGS_FOO': 'INVALID INT', 'A_SETTINGS_BAR': 1243},
            [(('A_SETTINGS_FOO', None), IntegerError)],
        ),
        (
            Settings2,
            (
                '{"settings_list": [], "settings": '
                '{"foo": 100, "bar": "INVALID FLOAT"}, "foo": []}'
            ),
            {},
            [
                (TextLocation(1, 55, 1, 70, 55, 69), FloatError),
                (TextLocation(1, 80, 1, 82, 80, 81), StrError),
            ],
        ),
        (
            Settings2,
            '{"settings_list": [], "settings": {"foo": 100}, "foo": []}',
            {'A_SETTINGS_BAR': 'INVALID FLOAT'},
            [
                (('A_SETTINGS_BAR', None), FloatError),
                (TextLocation(1, 56, 1, 58, 56, 57), StrError),
            ],
        ),
    ],
)
def test_validation_errors(model_cls, content, environ, locations):
    with raises(LoadingError) as exc_info:
        load_settings(
            model_cls,
            content,
            type_hint='json',
            load_env=True,
            environ=environ,
        )

    assert exc_info.type is LoadingValidationError
    assert [loc for loc, _ in per_location_errors(exc_info.value)] == [
        loc for loc, _ in locations
    ]
    assert [type(err) for _, err in per_location_errors(exc_info.value)] == [
        err_cls for _, err_cls in locations
    ]


def empty_tmp_file_creator(extension):
    def create():
        p = Path(tempfile.mktemp('.' + extension))
        p.touch()
        return p

    return create


@mark.parametrize(
    'any_content, load_env, type_hint, expect_err_msg',
    [
        (
            Path('/not/exists.cfg'),
            False,
            None,
            """LoadingError: Loader ".cfg" isn't supported""",
        ),
        ('', False, 'ini', """LoadingError: Loader "ini" isn't supported"""),
        (
            StringIO(''),
            False,
            'ini',
            """LoadingError: Loader "ini" isn't supported""",
        ),
        (
            StringIO(''),
            False,
            None,
            (
                'LoadingError: "type_hint" argument is '
                'required if content is not an '
                'instance of "pathlib.Path" class'
            ),
        ),
        (
            Path('/not/exists.cfg'),
            False,
            'DEFINITELY NOT A TYPE HINT',
            (
                'LoadingError: Loader "DEFINITELY NOT A TYPE HINT" '
                "isn't supported"
            ),
        ),
        (
            None,
            False,
            None,
            'LoadingError: no sources provided to load settings from',
        ),
    ],
)
def test_load_settings_general_errors(
    any_content, load_env, type_hint, expect_err_msg
):
    if callable(any_content):
        any_content = any_content()

    with raises(LoadingError) as err_info:
        load_settings(
            Settings2,
            any_content,
            load_env=load_env,
            type_hint=type_hint,
            _content_reader=lambda _: '',
        )

    assert str(err_info.value) == expect_err_msg


def test_file_not_found():
    path = Path(tempfile.mktemp())
    with raises(LoadingError) as err_info:
        load_settings(Settings2, path)

    assert isinstance(err_info.value.cause, FileNotFoundError)
    assert err_info.value.file_path == path
