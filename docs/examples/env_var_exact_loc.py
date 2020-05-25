from pydantic import ValidationError, IntegerError
from pydantic_settings import BaseSettingsModel, load_settings
from pydantic_settings.errors import ExtendedErrorWrapper


class Foo(BaseSettingsModel):
    val: int


try:
    load_settings(
        Foo, load_env=True, environ={'APP_val': 'NOT AN INT'}
    )
except ValidationError as e:
    err_wrapper, *_ = e.raw_errors
    assert isinstance(err_wrapper, ExtendedErrorWrapper)
    assert isinstance(err_wrapper.exc, IntegerError)
    assert err_wrapper.source_loc == 'APP_val'
