from pydantic_settings import BaseSettingsModel, load_settings


class Foo(BaseSettingsModel):
    val: int


assert load_settings(
    Foo, load_env=True, env_prefix='EX', environ={'EX_VAL': 10}
).val == 10
