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
                1,
                1,
                3,
                2,
                [
                    _create(2, 5, 2, 10, 12345, pos=6, end_pos=11),
                    _create(2, 12, 2, 17, 54321, pos=13, end_pos=18),
                ],
                pos=1,
                end_pos=20,
            ),
        ),
        (
            JSON_LIST_DICT,
            _create(
                1,
                1,
                5,
                2,
                [
                    _create(
                        2,
                        5,
                        4,
                        6,
                        {'key': _create(3, 16, 3, 21, 12345, pos=23, end_pos=28)},
                        pos=7,
                        end_pos=34,
                    )
                ],
                pos=1,
                end_pos=36,
            ),
        ),
        ('105', _create(1, 1, 1, 4, 105, pos=0, end_pos=3)),
        ('106.5', _create(1, 1, 1, 6, 106.5, pos=0, end_pos=5)),
        ('false', _create(1, 1, 1, 6, False, pos=0, end_pos=5)),
        ('true', _create(1, 1, 1, 5, True, pos=0, end_pos=4)),
        ('null', _create(1, 1, 1, 5, None, pos=0, end_pos=4)),
        ('[]', _create(1, 1, 1, 3, [], pos=1, end_pos=2)),
        (
            '[12, 23]',
            _create(
                1,
                1,
                1,
                9,
                [
                    _create(1, 2, 1, 4, 12, pos=1, end_pos=3),
                    _create(1, 6, 1, 8, 23, pos=5, end_pos=7),
                ],
                pos=1,
                end_pos=8,
            ),
        ),
        (
            '[{"key": 12345}]',
            _create(
                1,
                1,
                1,
                17,
                [
                    _create(
                        1,
                        2,
                        1,
                        16,
                        {'key': _create(1, 10, 1, 15, 12345, pos=9, end_pos=14)},
                        pos=2,
                        end_pos=15,
                    )
                ],
                pos=1,
                end_pos=16,
            ),
        ),
        ('{}', _create(1, 1, 1, 3, {}, pos=1, end_pos=2)),
        (
            '{"key": 1}',
            _create(
                1,
                1,
                1,
                11,
                {'key': _create(1, 9, 1, 10, 1, pos=8, end_pos=9)},
                pos=1,
                end_pos=10,
            ),
        ),
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
