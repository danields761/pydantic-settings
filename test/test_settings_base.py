import json

from pydantic import BaseModel, MissingError, ValidationError
from pytest import raises

from pydantic_settings.base import BaseSettingsModel
from pydantic_settings.errors import ExtendedErrorWrapper

from .conftest import Model1


class SettingModel1(BaseSettingsModel):
    class Baz(BaseModel):
        baf: Model1

    baz: Baz


def test_invalid_env_var_assignment():
    with raises(ValidationError) as exc_info:
        SettingModel1.from_env(
            {'APP_BAZ': 'SOMETHING DEFINITELY NOT A JSON OR TOML STRING'},
            ignore_restore_errs=False,
        )

    assert len(exc_info.value.raw_errors) == 2

    missing_field_err = exc_info.value.raw_errors[0]
    env_undecodable_value_err = exc_info.value.raw_errors[1]

    assert env_undecodable_value_err.loc_tuple() == ('baz',)
    assert isinstance(env_undecodable_value_err, ExtendedErrorWrapper)
    assert env_undecodable_value_err.source_loc == ('APP_BAZ', None)
    assert isinstance(env_undecodable_value_err.exc, json.JSONDecodeError)

    assert not isinstance(missing_field_err, ExtendedErrorWrapper)
    assert missing_field_err.loc_tuple() == ('baz',)
    assert isinstance(missing_field_err.exc, MissingError)


def test_settings_model():
    assert SettingModel1.from_env(
        {'APP_BAZ_BAF_FOO': 'TEST_VAL1', 'APP_BAZ_BAF_BAR': 'TEST_VAL2'}
    ) == SettingModel1(
        baz=SettingModel1.Baz(baf=Model1(foo='TEST_VAL1', bar='TEST_VAL2'))
    )


def test_settings_model_attrs_docs_created_automatically():
    class SettingsModel(BaseSettingsModel):
        class Config:
            build_attr_docs = True

        bar: int
        """bar description"""

    assert (
        SettingsModel.__fields__['bar'].field_info.description
        == 'bar description'
    )
