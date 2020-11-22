from typing import Callable, Optional, Type, TypeVar, Union, overload

from class_doc import extract_docs_from_cls_obj

from pydantic_settings.types import AnyPydanticModel, is_pydantic_dataclass


def apply_attributes_docs(
    model: Type[AnyPydanticModel], *, override_existing: bool = True
) -> None:
    """
    Apply model attributes documentation in-place. Resulted docs are placed
    inside :code:`field.schema.description` for *pydantic* model field.

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


MC = TypeVar('MC', bound=AnyPydanticModel)
_MC = TypeVar('_MC', bound=AnyPydanticModel)


@overload
def with_attrs_docs(model_cls: Type[MC]) -> Type[MC]:
    ...


@overload
def with_attrs_docs(
    *, override_existing: bool = True
) -> Callable[[Type[MC]], Type[MC]]:
    ...


def with_attrs_docs(
    model_cls: Optional[Type[MC]] = None, *, override_existing: bool = True
) -> Union[Callable[[Type[MC]], Type[MC]], Type[MC]]:
    """
    Applies :py:func:`.apply_attributes_docs`.
    """

    def decorator(maybe_model_cls: Type[_MC]) -> Type[_MC]:
        apply_attributes_docs(
            maybe_model_cls, override_existing=override_existing
        )
        return maybe_model_cls

    if model_cls is None:
        return decorator
    return decorator(model_cls)
