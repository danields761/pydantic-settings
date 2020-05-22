from typing import Any, Type, cast, Mapping, TypeVar, ClassVar

from pydantic import BaseModel, ValidationError

from pydantic_settings.attrs_docs import apply_attributes_docs
from pydantic_settings.decoder import json
from pydantic_settings.errors import ExtendedErrorWrapper, with_errs_locations
from pydantic_settings.restorer import ModelShapeRestorer
from pydantic_settings.utils import deep_merge_mappings


T = TypeVar('T', bound='SettingsModel')


class BaseSettingsModel(BaseModel):
    """
    Thin wrapper which combines :py:class:`pydantic.BaseModel` and
    :py:class:`.ModelShapeRestorer` for mapping env variables onto this model.
    """

    class Config:
        """
        Model behaviour configured with `Config` namespace traditionally for *pydantic*.
        """

        env_prefix: str = 'APP'
        """
        Expects that actual environ variables begins with given prefix, ex:
        :code:`'APP_FOO'` become :code:`model_instance['foo']`. Respects case
        sensitivity option.
        """

        env_case_sensitive: bool = False
        """
        Whether :py:class:`.ModelShapeRestorer` 
        will take environment variable case into account.
        """

        complex_inline_values_decoder = json.decode_document
        """
        Used to decode bunch of values for some nested namespace. Assume some
        nested namespace with 'foo' location and shape like
        :code:`{"bar": 1, "baz": "val"}`, then you able to set whole value with env 
        variable :command:`export APP_FOO='{"bar": 2, "baz": "new_val"}'`.
         """

        build_attr_docs: bool = True
        """
        Lookup and set model fields descriptions taken from attributes docstrings. Look
        :py:func:`.apply_attributes_docs` for further details.
        """

        override_exited_attrs_docs: bool = False
        """
        Override existed fields descriptions by attributes docs.
        """

    shape_restorer: ClassVar[ModelShapeRestorer]

    def __init_subclass__(cls, **kwargs):
        config = cast(cls.Config, cls.__config__)
        cls.shape_restorer = ModelShapeRestorer(
            cls,
            config.env_prefix,
            config.env_case_sensitive,
            config.complex_inline_values_decoder,
        )
        if config.build_attr_docs:
            apply_attributes_docs(
                cls, override_existing=config.override_exited_attrs_docs
            )

    @classmethod
    def from_env(
        cls: Type[T],
        environ: Mapping[str, str],
        *,
        ignore_restore_errs: bool = True,
        **vals: Any
    ) -> T:
        """
        Build model instance from given values and environ.

        :param environ: environment-like flat mapping, take precedence over values
        :param ignore_restore_errs: ignore errors happened while restoring flat-mapping
        :param vals: values
        :raises ValidationError: in case of failure
        :return: model instance
        """
        env_vars_applied, env_apply_errs = cls.shape_restorer.restore(environ)
        try:
            res = cls(**deep_merge_mappings(env_vars_applied, vals))
            validation_err = None
        except ValidationError as err:
            res = None
            validation_err = err

        if len(env_apply_errs) > 0 and not ignore_restore_errs:
            env_errs_as_ew = [
                ExtendedErrorWrapper(
                    env_err.__cause__ or env_err,
                    loc=tuple(env_err.loc),
                    source_loc=(env_err.key, None),
                )
                for env_err in env_apply_errs
            ]
            if validation_err is not None:
                validation_err.raw_errors += env_errs_as_ew
            else:
                validation_err = ValidationError(env_errs_as_ew, cls)

        if validation_err:
            raise with_errs_locations(cls, validation_err, env_vars_applied)

        return res
