import yaml
from pytest import mark
from inspect import cleandoc

from pydantic_settings.dumpers.common import CommentStr
from pydantic_settings.dumpers._yaml import _Dumper


# def test_path_rebuilder():
#     yaml.dump({'foo': ['bar', 'baz'], 'fee': {'bar': 1, 'baz': {}}}, Dumper=_Dumper)


@mark.parametrize(
    'source, result',
    [
        (
            {'a': {CommentStr('something interesting'): None, '1': 1}},
            """
            a:
                # something interesting
                '1': 1
            """,
        ),
        (
            {'a': {'1': 1, CommentStr('something interesting'): None, '2': 2}},
            """
            a:
                '1': 1
                # something interesting
                '2': 2
            """,
        ),
        (
            {'a': {'b': {CommentStr('something interesting'): None, '1': 1}}},
            """
            a:
                b:
                    # something interesting
                    '1': 1
            """,
        ),
        # (
        #     {
        #         'a': {
        #             CommentStr('not very interesting'): None,
        #             'b': {CommentStr('something interesting'): None, '1': 1},
        #         }
        #     },
        #     """
        #     a:
        #         # not very interesting
        #         b:
        #             # something interesting
        #             '1': 1
        #     """,
        # ),
        # (
        #     [CommentStr('test comment'), 1],
        #     """
        #     # test comment
        #     - 1
        #     """
        # ),
        # (
        #     [1, CommentStr('test comment'), 2],
        #     """
        #     - 1
        #     # test comment
        #     - 2
        #     """
        # ),
        # (
        #     {'a': [1, CommentStr('something interesting'), 2]},
        #     """
        #     a:
        #         - 1
        #         # something interesting
        #         - 2
        #     """,
        # ),
        # (
        #     {CommentStr('test comment'): None, 'a': {'b': 1, 'c': 2}},
        #     """
        #     # test comment
        #     a:
        #         b: 1
        #         c: 2
        #     """,
        # ),
    ],
)
def test_yaml_dump(source, result):
    assert yaml.dump(source, Dumper=_Dumper, indent=4) == cleandoc(result) + '\n'
