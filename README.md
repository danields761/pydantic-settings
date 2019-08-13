# Pydantic Settings

Library which extends **pydantic** functionality in scope of application settings.

Pydantic already have settings implementation, e.g. `pydantic.BaseSettings`, but from my point it's missing some useful features, listed below.

## Features

1. Point exact location of a failed field in the text
2. Override file values by environment variables, even if a field is nested

Allow to override values for nested fields if they are represented as *pydantic* model, `dataclass` or `attrs` dataclass. Here is example:

```python
@dataclass
class Nested:
    foo: int

class Settings(SettingsModel):
    nested: Nested


try:
    Settings.from_env({'APP_NESTED_FOO': 'NOT AN INT'})
except ValidationError as e:
    assert e.raw_errors[0].env_loc = 'APP_NESTED_FOO'
```

3. Shows right environment variable name for failed field

```python
try:
    Settings.from_env({'APP_nested_FOO': 'NOT AN INT'})
except ValidationError as e:
    assert e.raw_errors[0].env_loc = 'APP_nested_FOO'
```

4. Extracts field documentation from *Sphinx* style attributes documentation by processing AST tree of class definition

```python
class Foo(SettingsModel):
    class Config:
        extract_docs = True

    bar: str
    """here is docs"""

    #: this style is't supported, but probably will be added in future
    baz: int

assert Foo.__field__['bar'].schema.description == 'here is docs'
assert Foo.__field__['baz'].schema.description == ''  # :(
```

5. Render documentation examples with commentaries taken from fields description

```python
class Settings(SettingsModel):
    host: str = 'localhost'
    """
    Self domain name
    """

    auth_secret: SecretStr
    """
    Secret key used to encrypt user tokens with HMAC-SHA256
    """


EXAMPLE_SETTINGS = Settings(
    host='host.name',
    auth_secret='5O5qOWiM5qnvUwvQtP1_bUTonSIn7I7C66eqVGL2it0=',
)

assert dumper(EXAMPLE_SETTINGS, 'yaml') == """
# Self domain name
host: host.name

# Secret key used to encrypt user tokens with HMAC-SHA256
auth_secret: 5O5qOWiM5qnvUwvQtP1_bUTonSIn7I7C66eqVGL2it0
"""
```

## Development status

1. partially, only *json* and *yaml* supported for now
2. doesn't supports overriding inside list, case-sensitive implementation
3. done
4. done (*attr* classes not supported for now)
5. not started