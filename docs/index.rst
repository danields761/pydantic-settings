Pydantic Settings documentation (|version|)
===========================================

A set of tools helping to manage and work with application settings

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
order to use :py:func:`.load_settings` functionality. It also works with plain
:py:class:`pydantic.BaseModels` subclasses. Specify :py:obj:`~.load_settings.env_prefix`
in order to override default :code:`"APP"` prefix.

.. literalinclude:: examples/load_env_prefix.py
    :language: python


Rich location specifiers
------------------------

Also :py:func:`.load_settings` provides rich information about location
of a wrong value inside the source.

Location inside text content
............................

.. literalinclude:: examples/loc_inside_text_content.py
    :language: python


Location among environment variables
....................................

Also saves exact env variable name

.. literalinclude:: examples/env_var_exact_loc.py
    :language: python


Extract attributes docstrings
-----------------------------

By default, *pydantic* offers very verbose way of documenting fields, e.g.

.. code-block:: python

    class Foo(BaseModel):
        val: int = Schema(0, description='some valuable field description')

That verbosity may be avoided by extracting documentation from so called *attribute
docstring*, which is, for reference, also supported by *sphinx-autodoc*
(also there is very old rejected :pep:`224`, which proposes it), example:

.. literalinclude:: examples/attr_docs_example.py
    :language: python

:py:class:`.BaseSettingsModel` does it automatically.

.. note::
    Documented multiple-definitions inside class isn’t supported because it is
    really unclear to which of definitions the docstring should belongs


API Reference
-------------

Also there is :doc:`API Reference <autoapi/pydantic_settings/index>`.
It's a bit dirty, but still may provide helpful info.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
