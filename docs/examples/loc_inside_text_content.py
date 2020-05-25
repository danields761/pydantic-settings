from pydantic import ValidationError, IntegerError
from pydantic_settings import BaseSettingsModel, load_settings, TextLocation
from pydantic_settings.errors import ExtendedErrorWrapper


class Foo(BaseSettingsModel):
    val: int


try:
    load_settings(
        Foo, '{"val": "NOT AN INT"}'
    )
except ValidationError as e:
    err_wrapper, *_ = e.raw_errors
    assert isinstance(err_wrapper, ExtendedErrorWrapper)
    assert isinstance(err_wrapper.exc, IntegerError)
    assert err_wrapper.source_loc == TextLocation(
        1,  # starts from line
        9,  # starts from column
        1,  # ends on line
        20,  # ends on column
        8,  # begin index
        19  # end index
    )
