..
    AUTOGENERATED DO NOT MODIFY

Pydantic settings
*****************

..

   Hipster-orgazmic tool to mange application settings

.. image:: https://travis-ci.com/danields761/pydantic-settings.svg?branch=master
   :target: https://travis-ci.com/danields761/pydantic-settings
.. image:: https://badge.fury.io/py/pydantic-settings.svg
   :target: https://badge.fury.io/py/pydantic-settings
.. image:: https://readthedocs.org/projects/pydantic-settings/badge/?version=latest
   :target: https://pydantic-settings.readthedocs.io/en/latest/?badge=latest

Library which extends `pydantic <https://github.com/samuelcolvin/pydantic>`_ functionality in scope of application settings. *Pydantic* already have settings
implementation, e.g. ``pydantic.BaseSettings``, but from my point it’s missing some useful features:

1. Overriding settings values by environment variables even for nested fields

2. Providing detailed information about value location inside a loaded file or environment variable, which helps to point user mistake

3. Documenting model fields isn’t feels comfortable, but it’s really essential to write comprehensive documentation for application settings

..

   **NOTE:** Beta quality


Installation
============

Using pip:

.. code-block:: sh

   pip install pydantic-settings


Usage example
=============


Override values by env variables
--------------------------------

Allows to override values for nested fields if they are represented as *pydantic* model.

Here is example:

.. code-block:: python

   from pydantic import BaseModel
   from pydantic_settings import BaseSettingsModel, load_settings


   class ComponentOptions(BaseModel):
       val: str


   class AppSettings(BaseSettingsModel):
       class Config:
           env_prefix = 'FOO'

       component: ComponentOptions


   assert (
       load_settings(
           AppSettings,
           '{}',
           load_env=True,
           type_hint='json',
           environ={'FOO_COMPONENT_VAL': 'SOME VALUE'},
       ).component.val
       == 'SOME VALUE'
   )


Point exact error location inside file
--------------------------------------

.. code-block:: python

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


Extracts fields documentation
-----------------------------

Allows to extract *Sphinx* style attributes documentation by processing AST tree of class definition

.. code-block:: python

   from pydantic import BaseModel
   from pydantic_settings import with_attrs_docs


   @with_attrs_docs
   class Foo(BaseModel):
       bar: str
       """here is docs"""

       #: docs for baz
       baz: int

       #: yes
       #: of course
       is_there_multiline: bool = True


   assert Foo.__fields__['bar'].field_info.description == 'here is docs'
   assert Foo.__fields__['baz'].field_info.description == 'docs for baz'
   assert Foo.__fields__['is_there_multiline'].field_info.description == (
       'yes\nof course'
   )


Online docs
-----------

Read more detailed documentation on the project
`Read The Docs <https://pydantic-settings.readthedocs.io/en/latest/>`_ page.


Development setup
=================

Project requires `poetry <https://github.com/sdispater/poetry>`_ for development setup.

* If you aren’t have it already

.. code-block:: sh

   pip install poetry

* Install project dependencies

.. code-block:: sh

   poetry install

* Run tests

.. code-block:: sh

   poetry run pytest .

* Great, all works! Expect one optional step:

* Install `pre-commit <https://github.com/pre-commit/pre-commit>`_ for pre-commit hooks

.. code-block:: sh

   pip install pre-commit
   pre-commit install

That will install pre-commit hooks, which will check code with *flake8* and *black*.

..

   *NOTE* project uses **black** as code formatter, but i’am personally really dislike their
   *“double quoted strings everywhere”* style, that’s why ``black -S`` should be used
   (anyway it’s configured in *pyproject.toml* file)
