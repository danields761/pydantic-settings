from pytest import mark

import pydantic_settings.loaders.json
from pydantic_settings.loaders import json


_create = pydantic_settings.loaders.json.ASTItem.create


JSON_LIST = """[
    12345, 54321
]"""

JSON_LIST_DICT = """[
    {
        "key": 12345
    }
]"""


@mark.parametrize(
    'in_val, out_val',
    [
        (
            JSON_LIST,
            _create(
                1, 1, 3, 2, [_create(2, 5, 2, 10, 12345), _create(2, 12, 2, 17, 54321)]
            ),
        ),
        (
            JSON_LIST_DICT,
            _create(
                1, 1, 5, 2, [_create(2, 5, 4, 6, {'key': _create(3, 16, 3, 21, 12345)})]
            ),
        ),
        ('105', _create(1, 1, 1, 4, 105)),
        ('106.5', _create(1, 1, 1, 6, 106.5)),
        ('false', _create(1, 1, 1, 6, False)),
        ('true', _create(1, 1, 1, 5, True)),
        ('null', _create(1, 1, 1, 5, None)),
        ('[]', _create(1, 1, 1, 3, [])),
        (
            '[12, 23]',
            _create(1, 1, 1, 9, [_create(1, 2, 1, 4, 12), _create(1, 6, 1, 8, 23)]),
        ),
        (
            '[{"key": 12345}]',
            _create(
                1,
                1,
                1,
                17,
                [_create(1, 2, 1, 16, {'key': _create(1, 10, 1, 15, 12345)})],
            ),
        ),
        ('{}', _create(1, 1, 1, 3, {})),
        ('{"key": 1}', _create(1, 1, 1, 11, {'key': _create(1, 9, 1, 10, 1)})),
    ],
)
def test_json_ast1(in_val, out_val):
    assert json.loads(in_val) == out_val


@mark.parametrize(
    'in_val, out_json',
    [
        ('105', 105),
        ('106.5', 106.5),
        ('false', False),
        ('true', True),
        ('null', None),
        ('[]', []),
        ('[12, 23]', [12, 23]),
        ('[{"key": 12345}]', [{"key": 12345}]),
        ('{}', {}),
        ('{"key": 1}', {"key": 1}),
        ('{"key": "bar"}', {"key": "bar"}),
    ],
)
def test_get_json_value(in_val, out_json):
    assert json.loads(in_val).get_json_value() == out_json
