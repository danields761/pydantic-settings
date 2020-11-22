from pathlib import Path

from pydantic import FloatError
from pytest import mark

from pydantic_settings import LoadingValidationError, TextLocation
from pydantic_settings.errors import ExtendedErrorWrapper

from .test_settings_base import Model1


@mark.parametrize(
    'args, res',
    [
        (
            (
                [
                    ExtendedErrorWrapper(
                        FloatError(),
                        loc=('foo', 'bar'),
                        source_loc=(
                            'T_FOO_BAR',
                            TextLocation(1, 1, 1, 1, 10, 20),
                        ),
                    )
                ],
                Model1,
                None,
            ),
            (
                '1 validation error for Model1 '
                '(in-memory buffer and environment variables):\n'
                'foo -> bar from env "T_FOO_BAR" at 10:20\n'
                '\tvalue is not a valid float (type=type_error.float)'
            ),
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
                Model1,
                Path('/path/to/conf/file.json'),
            ),
            (
                '1 validation error for Model1 '
                '(configuration file at "/path/to/conf/file.json"):\n'
                'foo -> bar from file at 1:4\n'
                '\tvalue is not a valid float (type=type_error.float)'
            ),
        ),
    ],
)
def test_load_validation_err_rendering(args, res):
    assert LoadingValidationError(*args).render_error() == res
