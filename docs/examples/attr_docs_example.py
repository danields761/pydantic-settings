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
    'yes\n'
    'of course'
)
