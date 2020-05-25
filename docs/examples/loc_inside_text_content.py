from pydantic import ValidationError, IntegerError
from pydantic_settings import BaseSettingsModel, load_settings, TextLocation
from pydantic_settings.errors import ExtendedErrorWrapper


class Foo(BaseSettingsModel):
    val: int


try:
    load_settings(Foo, '{"val": "NOT AN INT"}', type_hint='json')
except ValidationError as e:
    err_wrapper, *_ = e.raw_errors
    assert isinstance(err_wrapper, ExtendedErrorWrapper)
    assert isinstance(err_wrapper.exc, IntegerError)
    assert err_wrapper.source_loc == TextLocation(
        line=1, col=9, end_line=1, end_col=21, pos=9, end_pos=20
    )
else:
    raise Exception('must rise error')
