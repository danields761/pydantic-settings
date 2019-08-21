import ast
import dataclasses
import inspect
import textwrap
from typing import Dict, Type, Mapping, Optional

import attr
from pydantic import BaseModel

from pydantic_settings.types import AnyModelType


def extract_class_attrib_docs(class_def: Type) -> Dict[str, str]:
    """
    Extract attributes documentation.

    :param class_def: type object (instances allowed as well) of a some class definition

    :raise ValueError: in case if given object can't provide sources.
    :raise TypeError: in case if object isn't a class definition

    :return: mapping "field name" => "extracted docstring"
    """
    # TODO
    #  class fields may be documented in class-docstring using "ivar", "var"
    #  or numpy "attributes" directives
    return extract_sphinx_class_attrib_docs(class_def)


def apply_attributes_docs(model: AnyModelType, *, override_existed: bool = True):
    """
    Apply model attributes documentation in-place. Resulted docs may be found inside
    :code:`field.schema.description` for *pydantic* model field,
    inside :code:`field.metadata['doc']` for *dataclass* field and inside
    :code:`attribute.metadata['doc']` for *attr* attribute. See
    :py:func:`.extract_class_attrib_docs` for more details how extraction is performed.

    :param model: either `pydantic.BaseModel` or `attr` or `dataclass`
    :param override_existed: override existing descriptions
    """
    docs = extract_class_attrib_docs(model)

    if issubclass(model, BaseModel):
        for field in model.__fields__.values():
            if field.schema.description and not override_existed:
                continue

            try:
                field.schema.description = docs[field.name]
            except KeyError:
                pass
    elif attr.has(model):
        # TODO figure out how attribute.metadata may be changed, since attr
        #  internals read-only
        raise NotImplementedError
    elif dataclasses.is_dataclass(model):
        for field in dataclasses.fields(model):
            if (
                isinstance(field.metadata, Mapping)
                and 'doc' in field.metadata
                and not override_existed
                or not isinstance(field.metadata, Mapping)
            ):
                continue

            try:
                field.metadata = {**(field.metadata or {}), 'doc': docs[field.name]}
            except KeyError:
                pass


def with_attrs_docs(
    model_cls: Optional[AnyModelType] = None, *, override_existed: bool = True
):
    """
    Decorator which applies :py:func:`.apply_attributes_docs`
    """

    def decorator(maybe_model_cls: AnyModelType):
        apply_attributes_docs(maybe_model_cls, override_existed=override_existed)
        return maybe_model_cls

    if model_cls is None:
        return decorator
    return decorator(model_cls)


def extract_ast_fields_docs_from_classdef(tree: ast.ClassDef) -> Dict[str, str]:
    """
    Extract Sphinx-style class attributes documentation from it AST-tree

    :param tree: class definition root node
    :return: mapping "field name" => "extracted docstring"
    """
    expect_str_def_for: str = ''
    collected: Dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            expect_str_def_for = node.target.id
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            expect_str_def_for = node.targets[0].id
        elif (
            (expect_str_def_for != '')
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Str)
        ):
            collected[expect_str_def_for] = inspect.cleandoc(node.value.s)
            expect_str_def_for = ''
        else:
            expect_str_def_for = ''

    return collected


def extract_sphinx_class_attrib_docs(model: Type) -> Dict[str, str]:
    """
    Extract Sphinx-style class attributes documentation from class definition.

    Doesn't performs lookup for base classes.

    Skips fields which is defined with multiple assignment syntax like :code:`foo, bar,
    ... = 'some', 'values', ...` because it really unclear, for which attribute the docs
    should be assigned.

    :param model: type object (instances allowed as well) of a some class definition

    :raise ValueError: in case if given object can't provide sources.
    :raise TypeError: in case if object isn't a class definition

    :return: mapping "field name" => "extracted docstring"
    """
    model_cls = model if isinstance(model, type) else type(model)
    try:
        sources = inspect.getsource(model_cls)
    except OSError as e:
        raise ValueError(f'unable to get "{model_cls}" sources') from e
    except TypeError as e:
        if 'is a built-in class' in str(e):
            raise ValueError(f'does not works with build-in objects') from e
        raise

    # clean indentation for inline class definitions
    sources = textwrap.dedent(sources)

    parsed = ast.parse(sources, inspect.getfile(model_cls))
    assert isinstance(parsed, ast.Module)
    definition = parsed.body[0]
    if not isinstance(definition, ast.ClassDef):
        raise TypeError(
            f'definition {model_cls} is not a class '
            f'definition, found root type {type(definition)}'
        )

    return extract_ast_fields_docs_from_classdef(definition)
