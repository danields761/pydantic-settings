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
        if field.field_info.description and not override_existing:
            continue

        try:
            field.field_info.description = '\n'.join(docs[field.name])
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
