Pydantic Settings documentation (|version|)
===========================================

A set of tools helping to work with and manage application settings

Getting Started
+++++++++++++++

*Pydantic Settings* package available on `PyPI <https://pypi.org/project/pydantic-settings/>`_

.. code-block:: shell

    pip install pydantic-settings


Manual by examples
++++++++++++++++++

Environment variables
---------------------

Override settings values by env variables even for nested fields

.. literalinclude:: examples/override_by_env.py
    :language: python

It's not necessary to override :py:class:`.BaseSettingsModel` in
order to use :py:func:`.load_settings` functionality, it also works with plain
:py:class:`pydantic.BaseModels` subclasses, probably, you need specify
:py:obj:`~.load_settings.env_prefix` to override default :code:`"APP"` prefix.

.. code-block:: python

    class Foo(BaseModel):
        val: int

    assert load_settings(
        Foo, load_env=True, env_prefix='EX', _environ={'EX_VAL': 10}
    ).val == 10


Rich location specifiers
------------------------

Also :py:func:`.load_settings` provides rich information about location
of an bad value inside the source.

Location inside text content
............................

.. code-block:: python

    class Foo(BaseModel):
        val: int

    try:
        load_settings(
            Foo, '{"val": "NOT AN INT"}'
        )
    except ValidationError as e:
        assert isinstance(e.raw_errors[0].exc, IntegerError)
        assert e.raw_errors[0].source_location = FileLocation(
            1,   # starts from line
            9,   # starts from column
            1,   # ends on line
            20,  # ends on column
            8,   # begin index
            19   # end index
        )

Location among environment variables
....................................

Also saves exact env variable name

.. code-block:: python

    class Foo(BaseModel):
        val: int


    try:
        load_settings(
            Foo, load_env=True, _environ={'APP_val': 'NOT AN INT'}
        )
    except ValidationError as e:
        assert isinstance(e.raw_errors[0].exc, IntegerError)
        assert e.raw_errors[0].source_location == 'APP_val'


Extract attributes docstrings
-----------------------------

By default, *pydantic* offers very verbose way for documenting fields, e.g.

.. code-block:: python

    class Foo(BaseModel):
        val: int = Field(0, description='some valuable field description')

That verbosity may be avoided by extracting documentation from so called *attributes
docstring*, which is, for reference, also supported by *sphinx-autodoc*
(also there is very old rejected :pep:`224`, which proposes it), example:

.. code-block:: python

    @with_attrs_docs
    class Foo(BaseModel):
        val: int
        """some valuable field description"""

    assert (
        Foo.__fields__['val'].schema.description
        == 'some valuable field description'
    )

:py:class:`.BaseSettingsModel` does it automatically.

.. note::
    Documented multiple-definitions inside class isn’t supported because it is
    really unclear to which of definitions the docstring should belongs


Known limitations/Bugs
----------------------

* There is no way to address model value inside a sequence by environment variable
* If you are settings *json* string as some nested namespace value via
  environment variable, and any value inside it will not pass validation,
  value of :py:obj:`~.ExtendedErrorWrapper.source_location` will be wrong.


API Reference
-------------

Also there is :doc:`API Reference <autoapi/pydantic_settings/index>`.
It's dirty, but still may provide helpful info.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
