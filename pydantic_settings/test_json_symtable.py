import pytest

from pydantic_settings._loc_mapping import build_symtable, SymbolLocation
import yaml

_SIMPLE_JSON_1_VALUE = """{
    "val": 1
}"""

_SIMPLE_JSON_1_VALUE_WITH_WHITESPACE = '   \t' + _SIMPLE_JSON_1_VALUE


@pytest.mark.parametrize(
    'json_content, symtable',
    [
        (
            _SIMPLE_JSON_1_VALUE,
            {
                'val': SymbolLocation(
                    lineno=2, coloffset=12, end_lineno=2, end_coloffset=13
                )
            },
        )
    ],
)
def test_json_symtable_build(json_content, symtable):
    assert build_symtable(json_content) == symtable
