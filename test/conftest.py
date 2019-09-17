from dataclasses import dataclass

from _pytest.fixtures import fixture
from attr import dataclass as attr_dataclass
from pydantic import BaseModel


class Model1(BaseModel):
    foo: str
    bar: str


@fixture
def model2_cls():
    class Model2(BaseModel):
        @dataclass
        class Foo:
            bar: int
            baz: str

        foo: Foo

    return Model2


@fixture
def model3_cls():
    class Model3(BaseModel):
        @attr_dataclass
        class Foo:
            bar: int
            baz: str

        foo: Foo

    return Model3


@dataclass
class Model4:
    class Foo(BaseModel):
        bar: int
        baz: str

    foo: Foo


@attr_dataclass
class Model5:
    class Foo(BaseModel):
        bar: int
        baz: str

    foo: Foo


class Model6(BaseModel):
    class Baz(BaseModel):
        bam: Model1

    baz: Baz
    baf: Model1
