import ast
import inspect
import textwrap
from typing import Dict, Type, Optional

from class_doc import extract_docs_from_cls_obj

from pydantic_settings.types import (
    AnyPydanticModel,
    PydanticDataclass,
    is_pydantic_dataclass,
)


def apply_attributes_docs(
    model: Type[AnyPydanticModel], *, override_existing: bool = True
):
    """
    Apply model attributes documentation in-place. Resulted docs may be found inside
    :code:`field.schema.description` for *pydantic* model field

    :param model: any pydantic model
    :param override_existing: override existing descriptions
    """
    if is_pydantic_dataclass(model):
        apply_attributes_docs(
            model.__pydantic_model__, override_existing=override_existing
        )
        return

    docs = extract_docs_from_cls_obj(model)

    for field in model.__fields__.values():
        if field.schema.description and not override_existing:
            continue

        try:
            field.schema.description = docs[field.name]
        except KeyError:
            pass


def with_attrs_docs(
    model_cls: Optional[AnyPydanticModel] = None, *, override_existed: bool = True
):
    """
    Decorator which applies :py:func:`.apply_attributes_docs`
    """

    def decorator(maybe_model_cls: AnyPydanticModel):
        apply_attributes_docs(maybe_model_cls, override_existing=override_existed)
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
