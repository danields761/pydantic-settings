from pydantic import BaseModel
from pydantic_settings import load_settings


class Foo(BaseModel):
    val: int


assert (
    load_settings(
        Foo, load_env=True, env_prefix='EX', environ={'EX_VAL': '10'}
    ).val
    == 10
)
