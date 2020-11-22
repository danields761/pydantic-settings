from typing import List, Tuple, Union

from pydantic import BaseModel
from pytest import mark

from pydantic_settings import TextLocation
from pydantic_settings.decoder.json import decode_document
from pydantic_settings.restorer import (
    ModelShapeRestorer,
    _build_model_flat_map,
)

from .conftest import Model1, Model4, Model5, Model6


class YAModel(BaseModel):
    list: List[str]


class WithComplexTypes(BaseModel):
    list: List[str]  # will be ignored because not supported
    tuple: Tuple[str]
    union: Union[str, int, bool]  # path pointer end here
    models_union: Union[Model1, YAModel]  # will expand nested path
    # expand first model, but still allow this point
    model_union_with_simple: Union[Model1, int]


def test_with_complex_types():
    assert {
        key: tuple(val)
        for key, val in _build_model_flat_map(
            WithComplexTypes, 't', str.casefold
        ).items()
    } == {
        't_list': (('list',), False, False),
        't_tuple': (('tuple',), False, False),
        't_union': (('union',), False, False),
        't_models_union': (('models_union',), True, True),
        't_models_union_foo': (('models_union', 'foo'), False, False),
        't_models_union_bar': (('models_union', 'bar'), False, False),
        't_models_union_list': (('models_union', 'list'), False, False),
        't_model_union_with_simple': (
            ('model_union_with_simple',),
            True,
            False,
        ),
        't_model_union_with_simple_foo': (
            ('model_union_with_simple', 'foo'),
            False,
            False,
        ),
        't_model_union_with_simple_bar': (
            ('model_union_with_simple', 'bar'),
            False,
            False,
        ),
    }


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
    'model_cls, input_val, result, locations',
    [
        (
            Model1,
            {'test_foo': 'VAL1', 'test_bar': 'VAL2'},
            {'foo': 'VAL1', 'bar': 'VAL2'},
            {('foo',): ('test_foo', None), ('bar',): ('test_bar', None)},
        ),
        (
            Model4,
            {'test_foo': '{"bar": "VAL1", "baz": "VAL2"}'},
            {'foo': {'bar': 'VAL1', 'baz': 'VAL2'}},
            {
                ('foo', 'bar'): (
                    'test_foo',
                    TextLocation(
                        line=1,
                        col=9,
                        end_line=1,
                        end_col=15,
                        pos=9,
                        end_pos=14,
                    ),
                ),
                ('foo', 'baz'): (
                    'test_foo',
                    TextLocation(
                        line=1,
                        col=24,
                        end_line=1,
                        end_col=30,
                        pos=24,
                        end_pos=29,
                    ),
                ),
            },
        ),
        (
            Model4,
            {'test_foo_bar': 'VAL1', 'test_foo_baz': 'VAL2'},
            {'foo': {'bar': 'VAL1', 'baz': 'VAL2'}},
            {
                ('foo', 'bar'): ('test_foo_bar', None),
                ('foo', 'baz'): ('test_foo_baz', None),
            },
        ),
        (
            Model4,
            {'test_foo_bar': 'VAL1'},
            {'foo': {'bar': 'VAL1'}},
            {('foo', 'bar'): ('test_foo_bar', None)},
        ),
        (
            Model6,
            {'test_baz_bam_foo': 'VAL1', 'test_baz_bam_bar': 'VAL2'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
            {
                ('baz', 'bam', 'foo'): ('test_baz_bam_foo', None),
                ('baz', 'bam', 'bar'): ('test_baz_bam_bar', None),
            },
        ),
        (
            Model6,
            {'test_baz_bam': '{"foo": "VAL1", "bar": "VAL2"}'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
            {
                ('baz', 'bam', 'foo'): (
                    'test_baz_bam',
                    TextLocation(
                        line=1,
                        col=9,
                        end_line=1,
                        end_col=15,
                        pos=9,
                        end_pos=14,
                    ),
                ),
                ('baz', 'bam', 'bar'): (
                    'test_baz_bam',
                    TextLocation(
                        line=1,
                        col=24,
                        end_line=1,
                        end_col=30,
                        pos=24,
                        end_pos=29,
                    ),
                ),
            },
        ),
        (
            Model6,
            {'test_baz': '{"bam": {"foo": "VAL1", "bar": "VAL2"}}'},
            {'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}}},
            {
                ('baz', 'bam', 'foo'): (
                    'test_baz',
                    TextLocation(
                        line=1,
                        col=17,
                        end_line=1,
                        end_col=23,
                        pos=17,
                        end_pos=22,
                    ),
                )
            },
        ),
        (
            Model6,
            {
                'test_baz_bam_foo': 'VAL1',
                'test_baz_bam_bar': 'VAL2',
                'test_baf_foo': 'VAL3',
            },
            {
                'baz': {'bam': {'foo': 'VAL1', 'bar': 'VAL2'}},
                'baf': {'foo': 'VAL3'},
            },
            {
                ('baz', 'bam', 'foo'): ('test_baz_bam_foo', None),
                ('baz', 'bam', 'bar'): ('test_baz_bam_bar', None),
                ('baf', 'foo'): ('test_baf_foo', None),
            },
        ),
    ],
)
def test_restore_model(model_cls, input_val, result, locations):
    values, errs = ModelShapeRestorer(
        model_cls, 'TEST', False, decode_document
    ).restore(input_val)
    assert values, errs == (result, [])

    assert {loc: values.get_location(loc) for loc in locations} == locations
