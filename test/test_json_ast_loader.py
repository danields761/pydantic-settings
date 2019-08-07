from __future__ import annotations

from pytest import mark

from pydantic_settings.loaders import json


_create = json.ASTItem.create


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
            _create([_create(12345, 2, 5, 2, 10), _create(54321, 2, 12, 2, 17)], 1, 1, 3, 1),
        ),
        (
            JSON_LIST_DICT,
            _create(
                [_create({'key': _create(12345, 3, 16, 3, 21)}, 2, 5, 4, 5)],
                1,
                1,
                5,
                1,
            ),
        ),
        ('105', _create(105, 1, 1, 1, 3)),
        ('106.5', _create(106.5, 1, 1, 1, 5)),
        ('false', _create(False, 1, 1, 1, 5)),
        ('true', _create(True, 1, 1, 1, 4)),
        ('null', _create(None, 1, 1, 1, 4)),
        ('[]', _create([], 1, 1, 1, 2)),
        (
            '[12, 23]',
            _create([_create(12, 1, 1, 1, 3), _create(23, 1, 5, 1, 7)], 1, 1, 1, 8),
        ),
        (
            '[{"key": 12345}]',
            _create(
                [_create({'key': _create(12345, 1, 9, 1, 14)}, 1, 2, 1, 15)],
                1,
                1,
                1,
                16,
            ),
        ),
        ('{}', _create({}, 1, 1, 1, 2)),
        ('{"key": 1}', _create({'key': _create(1, 1, 8, 1, 9)}, 1, 1, 1, 10)),
    ],
)
def test_json_ast1(in_val, out_val):
    assert json.loads(in_val) == out_val
