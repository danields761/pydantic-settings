from pathlib import Path

from pydantic import FloatError
from pytest import mark

from pydantic_settings import LoadingValidationError, TextLocation
from pydantic_settings.errors import ExtendedErrorWrapper


@mark.parametrize(
    'args, res',
    [
        (
            (
                [
                    ExtendedErrorWrapper(
                        FloatError(),
                        loc=('foo', 'bar'),
                        source_loc=('T_FOO_BAR', TextLocation(1, 1, 1, 1, 10, 20)),
                    )
                ],
                None,
            ),
            """1 validation errors while loading settings from in-memory configuration text and environment variables:
foo -> bar from env "T_FOO_BAR" [10:20]
  value is not a valid float (type=type_error.float)""",
        ),
        (
            (
                [
                    ExtendedErrorWrapper(
                        FloatError(),
                        loc=('foo', 'bar'),
                        source_loc=TextLocation(1, 4, 1, 1, 10, 20),
                    )
                ],
                Path('/path/to/conf/file.json'),
            ),
            """1 validation errors while loading settings from configuration file at "/path/to/conf/file.json":
foo -> bar from file at 1 line 4 column
  value is not a valid float (type=type_error.float)""",
        ),
    ],
)
def test_load_validation_err_rendering(args, res):
    assert LoadingValidationError(*args).render_error() == res
