from pydantic import BaseModel

from pydantic_settings import BaseSettingsModel, load_settings


class ComponentOptions(BaseModel):
    val: str


class AppSettings(BaseSettingsModel):
    class Config:
        env_prefix = 'FOO'

    component: ComponentOptions


assert load_settings(
    AppSettings,
    '{}',
    load_env=True,
    type_hint='json',
    _environ={'FOO_COMPONENT_VAL': 'SOME VALUE'}
).component.val == 'SOME VALUE'
