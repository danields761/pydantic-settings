# Pydantic settings
> Hipster-orgazmic tool to mange application settings

[![Build Status](https://travis-ci.com/danields761/pydantic-settings.svg?branch=master)](https://travis-ci.com/danields761/pydantic-settings)
[![PyPI version](https://badge.fury.io/py/pydantic-settings.svg)](https://badge.fury.io/py/pydantic-settings)
[![Documentation Status](https://readthedocs.org/projects/pydantic-settings/badge/?version=latest)](https://pydantic-settings.readthedocs.io/en/latest/?badge=latest)

Library which extends [__pydantic__](https://github.com/samuelcolvin/pydantic) functionality in scope of application settings. *Pydantic* already have settings
implementation, e.g. `pydantic.BaseSettings`, but from my point it's missing some useful features:

1. Overriding settings values by environment variables even for nested fields
2. Providing detailed information about value location inside a loaded file or environment variable, which helps to point user mistake
3. Documenting model fields isn't feels comfortable, but it's really essential to write comprehensive documentation for application settings

> __NOTE:__ Alpha quality

## Installation

Using pip:

```sh
pip install pydantic-settings
```

## Usage example

### Override values by env variables

Allows to override values for nested fields if they are represented as *pydantic* model.

Here is example:

```python
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettingsModel

class Nested(BaseModel):
    foo: int

class Settings(BaseSettingsModel):
    nested: Nested


try:
    Settings.from_env({'APP_nested_FOO': 'NOT AN INT'})
except ValidationError as e:
    assert e.raw_errors[0].env_loc == 'APP_nested_FOO'  # shows exact env variable name
```

### Point exact error location inside file

```python
from pydantic import BaseModel, IntegerError
from pydantic_settings import BaseSettingsModel, LoadingValidationError, load_settings, FileLocation

class Nested(BaseModel):
    foo: int

class Settings(BaseSettingsModel):
    nested: Nested

conf_text = """
nested:
    foo: 'NOT AN INT'
"""

try:
    load_settings(Settings, conf_text, type_hint='yaml')
except LoadingValidationError as e:
    assert e.raw_errors[0].loc == ('nested', 'foo')
    assert e.raw_errors[0].text_loc == FileLocation(line=3, col=10, end_line=3, end_col=22)
    assert isinstance(e.raw_errors[0].exc, IntegerError)

```


### Extracts fields documentation

Allows to extract *Sphinx* style attributes documentation by processing AST tree of class definition

```python
from pydantic_settings import BaseSettingsModel

class Foo(BaseSettingsModel):
    class Config:
        build_attr_docs = True

    bar: str
    """here is docs"""

    #: this style is't supported, but probably will be added in future
    baz: int

assert Foo.__fields__['bar'].schema.description == 'here is docs'
assert Foo.__fields__['baz'].schema.description is None  # :(
```

### Online docs

Read more detailed documentation on the project
[Read The Docs](https://pydantic-settings.readthedocs.io/en/latest/) page.

## Development setup

Project requires [__poetry__](https://github.com/sdispater/poetry) for development setup.

* If you aren't have it already

```sh
pip install poetry
``` 

* Install project dependencies

```sh
poetry install
```

* Run tests

```sh
poetry run pytest .
```

* Great, all works! Expect one optional step:

* Install [__pre-commit__](https://github.com/pre-commit/pre-commit) for pre-commit hooks

```sh
pip install pre-commit
pre-commit install
```

That will install pre-commit hooks, which will check code with *flake8* and *black*.

> *NOTE* project uses __black__ as code formatter, but i'am personally really dislike their
> *"double quoted strings everywhere"* style, that's why `black -S` should be used
> (anyway it's configured in *pyproject.toml* file)