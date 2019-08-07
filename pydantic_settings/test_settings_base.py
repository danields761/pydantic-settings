import toml
import yaml
from attr import dataclass as attr_dataclass
from pydantic import BaseModel
from dataclasses import dataclass

from pytest import fixture, mark
from pydantic_settings.base import _build_model_flat_map, FlatMapRestorer, SettingsModel


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


class Model7(BaseModel):
    pass


def test_flat_model():
    assert _build_model_flat_map(Model1, 'test', str.casefold) == {
        'test_foo': (['foo'], False),
        'test_bar': (['bar'], False),
    }


@mark.parametrize('model_cls', [Model4, Model5])
def test_complex_nested_models(model_cls):
    assert _build_model_flat_map(model_cls, 'test', str.casefold) == {
        'test_foo': (['foo'], True),
        'test_foo_bar': (['foo', 'bar'], False),
        'test_foo_baz': (['foo', 'baz'], False),
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
            {'test_foo': "{bar = 'VAL1', baz = 'VAL2'}"},
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
            {'test_baz_bam': "{foo = 'VAL1', bar = 'VAL2'}"},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
        ),
        (
            Model6,
            {'test_baz': "{bam = {foo = 'VAL1', bar = 'VAL2'}}"},
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
    target = {}
    FlatMapRestorer(model_cls, 'TEST', True, toml.loads).apply_values(target, input_val)
    assert target == result


@mark.parametrize(
    'model_cls, input_val, result, target_factory',
    [
        (
            Model6,
            {
                'test_baz_bam_foo': 'RES_VAL1',
                'test_baz_bam_bar': 'RES_VAL2',
                'test_baf_foo': 'RES_VAL3',
            },
            {
                'baz': {'bam': Model1(foo='RES_VAL1', bar='RES_VAL2')},
                'baf': Model1(foo='RES_VAL3', bar='VAL4'),
            },
            lambda: {
                'baz': {'bam': Model1(foo='VAL1', bar='VAL2')},
                'baf': Model1(foo='VAL3', bar='VAL4'),
            },
        )
    ],
)
def test_apply_on_model(model_cls, input_val, result, target_factory):
    target = target_factory()
    FlatMapRestorer(model_cls, 'TEST', True, toml.loads).apply_values(target, input_val)
    assert target == result


class SettingModel1(SettingsModel):
    class Baz(BaseModel):
        baf: Model1

    baz: Baz


def test_settings_model():
    assert SettingModel1.from_env(
        {'APP_BAZ_BAF_FOO': 'TEST_VAL1', 'APP_BAZ_BAF_BAR': 'TEST_VAL2'}
    ) == SettingModel1(
        baz=SettingModel1.Baz(baf=Model1(foo='TEST_VAL1', bar='TEST_VAL2'))
    )
