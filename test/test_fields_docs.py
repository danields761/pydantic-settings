import dataclasses

import attr
from pydantic import BaseModel, Schema
from pytest import mark

from pydantic_settings.attrs_docs import extract_class_attrib_docs, with_attrs_docs


class SphinxLikeAttribDocs:
    foo: int
    """foo description"""

    bar: str
    """
    bar
    super
    long
    ...
    ...
    description
    """

    baz: str = ''
    """baz description"""

    baf = ''
    """baf description"""


def test_extract_sphinx_class_attrib_docs():
    docs = extract_class_attrib_docs(SphinxLikeAttribDocs)
    assert all(f in docs for f in ('foo', 'bar', 'baz', 'baf'))

    assert 'foo description' == docs['foo']
    assert 'bar\nsuper\nlong\n...\n...\ndescription' == docs['bar']
    assert 'baz description' == docs['baz']
    assert 'baf description' == docs['baf']


def test_extract_sphinx_class_attrib_docs_from_inline_def():
    class Inline:
        bar: int
        """bar description"""

    docs = extract_class_attrib_docs(Inline)
    assert docs['bar'] == 'bar description'


class ClassDocAttribDocs:
    """
    :ivar bar: bar description
    :var baz: baz description
    :var baf: baf
    long
    description
    """

    bar: int
    baz: int
    baf: int


@mark.xfail(reason='not yet implemented')
def test_extract_docstring_class_attrib_docs():
    docs = extract_class_attrib_docs(ClassDocAttribDocs)
    assert 'bar description' == docs['bar']
    assert 'baz description' == docs['baz']
    assert 'baf\nlong\ndeinition' == docs['baf']


def test_pydantic_model_field_description():
    @with_attrs_docs
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].schema.description
        == 'bar description'
    )


def test_pydantic_model_field_description_with_overriding():
    @with_attrs_docs(override_existed=True)
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int = Schema(0, description='TEST OLD DESCRIPTION')
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].schema.description
        == 'bar description'
    )


def test_pydantic_model_field_description_without_overriding():
    @with_attrs_docs(override_existed=False)
    class PydanticModelFieldDocsModel(BaseModel):
        bar: int = Schema(0, description='TEST OLD DESCRIPTION')
        """bar description"""

    assert (
        PydanticModelFieldDocsModel.__fields__['bar'].schema.description
        == 'TEST OLD DESCRIPTION'
    )


def test_dataclass_model_field_description():
    @with_attrs_docs
    @dataclasses.dataclass
    class DataclassFieldDocsModel:
        bar: int
        """bar description"""

    assert (
        DataclassFieldDocsModel.__dataclass_fields__['bar'].metadata['doc']
        == 'bar description'
    )


def test_dataclass_model_field_description_with_overriding():
    @with_attrs_docs(override_existed=True)
    @dataclasses.dataclass
    class DataclassFieldDocsModel:
        bar: int = dataclasses.field(metadata={'doc': 'TEST OLD DESCRIPTION'})
        """bar description"""

    assert (
        DataclassFieldDocsModel.__dataclass_fields__['bar'].metadata['doc']
        == 'bar description'
    )


def test_dataclass_model_field_description_without_overriding():
    @with_attrs_docs(override_existed=False)
    @dataclasses.dataclass
    class DataclassFieldDocsModel:
        bar: int = dataclasses.field(metadata={'doc': 'TEST OLD DESCRIPTION'})
        """bar description"""

    assert (
        DataclassFieldDocsModel.__dataclass_fields__['bar'].metadata['doc']
        == 'TEST OLD DESCRIPTION'
    )


@mark.xfail(reason='not implemented due to attr technical details')
def test_attrs_model_field_description():
    @with_attrs_docs
    @attr.dataclass
    class AttrsFieldDocsModel:
        bar: int
        """bar description"""

    assert AttrsFieldDocsModel.__attrs_attrs__.bar.metadata['doc'] == 'bar description'


@mark.xfail(reason='not implemented due to attr technical details')
def test_attrs_model_field_description_with_overriding():
    @with_attrs_docs(override_existed=True)
    @attr.dataclass
    class AttrsFieldDocsModel:
        bar: int = attr.attrib(metadata={'doc': 'TEST OLD DESCRIPTION'})
        """bar description"""

    assert AttrsFieldDocsModel.__attrs_attrs__.bar.metadata['doc'] == 'bar description'


@mark.xfail(reason='not implemented due to attr technical details')
def test_attrs_model_field_description_without_overriding():
    @with_attrs_docs(override_existed=False)
    @attr.dataclass
    class AttrsFieldDocsModel:
        bar: int = attr.attrib(metadata={'doc': 'TEST OLD DESCRIPTION'})
        """bar description"""

    assert (
        AttrsFieldDocsModel.__attrs_attrs__.bar.metadata['doc']
        == 'TEST OLD DESCRIPTION'
    )
