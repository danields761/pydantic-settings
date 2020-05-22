import dataclasses

import attr
from pydantic import BaseModel, Schema, Field
from pytest import mark

from pydantic_settings.attrs_docs import with_attrs_docs


def test_pydantic_model_field_description():
    @with_attrs_docs
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].field_info.description
        == 'bar description'
    )


def test_pydantic_model_field_description_with_overriding():
    @with_attrs_docs(override_existed=True)
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int = Field(0, description='TEST OLD DESCRIPTION')
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].field_info.description
        == 'bar description'
    )


def test_pydantic_model_field_description_without_overriding():
    @with_attrs_docs(override_existed=False)
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int = Field(0, description='TEST OLD DESCRIPTION')
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].field_info.description
        == 'TEST OLD DESCRIPTION'
    )
