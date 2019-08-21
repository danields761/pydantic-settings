import json
from dataclasses import dataclass

from attr import dataclass as attr_dataclass
from pydantic import BaseModel, ValidationError, MissingError
from pytest import fixture, mark, raises

from pydantic_settings.base import ModelShapeRestorer, BaseSettingsModel
from pydantic_settings.model_shape_restorer import _build_model_flat_map
from pydantic_settings.errors import ExtendedErrorWrapper


class Model1(BaseModel):
    foo: str
    bar: str


@fixture
def model2_cls():
    class Model2(BaseModel):
        @dataclass
        class Foo:
            bar: int
            baz: str

        foo: Foo

    return Model2


@fixture
def model3_cls():
    class Model3(BaseModel):
        @attr_dataclass
        class Foo:
            bar: int
            baz: str

        foo: Foo

    return Model3


@dataclass
class Model4:
    class Foo(BaseModel):
        bar: int
        baz: str

    foo: Foo


@attr_dataclass
class Model5:
    class Foo(BaseModel):
        bar: int
        baz: str

    foo: Foo


class Model6(BaseModel):
    class Baz(BaseModel):
        bam: Model1

    baz: Baz
    baf: Model1


def test_flat_model():
    assert _build_model_flat_map(Model1, 'test', str.casefold) == {
        'test_foo': (('foo',), False, False),
        'test_bar': (('bar',), False, False),
    }


@mark.parametrize('model_cls', [Model4, Model5])
def test_complex_nested_models(model_cls):
    assert _build_model_flat_map(model_cls, 'test', str.casefold) == {
        'test_foo': (('foo',), True, True),
        'test_foo_bar': (('foo', 'bar'), False, False),
        'test_foo_baz': (('foo', 'baz'), False, False),
    }


@mark.parametrize(
    'model_cls, input_val, result',
    [
        (
            Model1,
            {'test_foo': 'VAL1', 'test_bar': 'VAL2'},
            {'foo': 'VAL1', 'bar': 'VAL2'},
        ),
        (
            Model4,
            {'test_foo': '{"bar": "VAL1", "baz": "VAL2"}'},
            {'foo': {'bar': 'VAL1', 'baz': 'VAL2'}},
        ),
        (
            Model4,
            {'test_foo_bar': 'VAL1', 'test_foo_baz': 'VAL2'},
            {'foo': {'bar': 'VAL1', 'baz': 'VAL2'}},
        ),
        (Model4, {'test_foo_bar': 'VAL1'}, {'foo': {'bar': 'VAL1'}}),
        (
            Model6,
            {'test_baz_bam_foo': 'VAL1', 'test_baz_bam_bar': 'VAL2'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
        ),
        (
            Model6,
            {'test_baz_bam': '{"foo": "VAL1", "bar": "VAL2"}'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
        ),
        (
            Model6,
            {'test_baz': '{"bam": {"foo": "VAL1", "bar": "VAL2"}}'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
        ),
        (
            Model6,
            {
                'test_baz_bam_foo': 'VAL1',
                'test_baz_bam_bar': 'VAL2',
                'test_baf_foo': 'VAL3',
            },
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}, 'baf': {'foo': 'VAL3'}},
        ),
    ],
)
def test_restore_model(model_cls, input_val, result):
    assert ModelShapeRestorer(model_cls, 'TEST', False, json.loads).restore(
        input_val
    ) == (result, [])


class SettingModel1(BaseSettingsModel):
    class Baz(BaseModel):
        baf: Model1

    baz: Baz


def test_invalid_env_var_assignment():
    with raises(ValidationError) as exc_info:
        SettingModel1.from_env(
            {'APP_BAZ': 'SOMETHING DEFINITELY NOT A JSON OR TOML STRING'},
            ignore_restore_errs=False,
        )

    assert len(exc_info.value.raw_errors) == 2

    missing_field_err = exc_info.value.raw_errors[0]
    env_undecodable_value_err = exc_info.value.raw_errors[1]

    assert env_undecodable_value_err.loc == ('baz',)
    assert isinstance(env_undecodable_value_err, ExtendedErrorWrapper)
    assert env_undecodable_value_err.source_loc == 'APP_BAZ'
    assert isinstance(env_undecodable_value_err.exc, json.JSONDecodeError)

    assert not isinstance(missing_field_err, ExtendedErrorWrapper)
    assert missing_field_err.loc == ('baz',)
    assert isinstance(missing_field_err.exc, MissingError)


def test_settings_model():
    assert SettingModel1.from_env(
        {'APP_BAZ_BAF_FOO': 'TEST_VAL1', 'APP_BAZ_BAF_BAR': 'TEST_VAL2'}
    ) == SettingModel1(
        baz=SettingModel1.Baz(baf=Model1(foo='TEST_VAL1', bar='TEST_VAL2'))
    )


def test_settings_model_attrs_docs_created_automatically():
    class SettingsModel(BaseSettingsModel):
        class Config:
            build_attr_docs = True

        bar: int
        """bar description"""

    assert SettingsModel.__fields__['bar'].schema.description == 'bar description'
