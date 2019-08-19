from pytest import raises

from pydantic_settings.utils import deep_merge_mappings


def test_simple_chain_map_possibilities():
    m = deep_merge_mappings(deep_merge_mappings({'a': 1}, {'a': 2, 'b': 2}), {'c': 3})
    assert m['a'] == 1
    assert m['b'] == 2
    assert m['c'] == 3


def test_nested_map():
    m = deep_merge_mappings({'a': {'aa': 1}}, {'a': {'aa': 2, 'bb': 2}})
    assert m['a']['aa'] == 1
    assert m['a']['bb'] == 2


def test_simple_values_priority():
    m = deep_merge_mappings({'a': 1}, {'a': {'aa': 2}})
    assert m['a'] == 1
    with raises(TypeError) as exc_info:
        _ = m['a']['aa']
    assert exc_info.value.args[0] == "'int' object is not subscriptable"
