import yaml
from pytest import mark
from inspect import cleandoc

from pydantic_settings.dumpers.common import CommentStr
from pydantic_settings.dumpers._yaml import _Dumper


def test_path_rebuilder():
    yaml.dump({'foo': ['bar', 'baz'], 'fee': {'bar': 1}}, Dumper=_Dumper)


@mark.parametrize(
    'source, result',
    [
        (
            {'a': {CommentStr('something interesting'): None, '1': 1, '2': 2, '3': 3}},
            """
            a:
                # Something interesting
                '1': 1
                '2': 2
                '3': 3
            """,
        )
    ],
)
def test_yaml_dump(source, result):
    result_lines = result.split('\n')
    if len(result_lines[0].strip()) == 0:
        result_lines = result_lines[1:]

    assert yaml.dump(source) == cleandoc('\n'.join(result_lines))
