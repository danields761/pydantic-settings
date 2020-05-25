from dataclasses import asdict
from pathlib import Path
from typing import (
    Any,
    Optional,
    Tuple,
    Sequence,
    Union,
    Iterator,
    Iterable,
    Type,
    Dict,
    cast,
    List,
)

from pydantic import ValidationError, BaseModel, BaseConfig
from pydantic.error_wrappers import ErrorWrapper, error_dict

from pydantic_settings.decoder import DecoderMeta
from pydantic_settings.types import (
    TextLocation,
    AnySourceLoc,
    JsonDict,
    ModelLoc,
    Json,
    AnySourceLocProvider,
)


class LoadingError(ValueError):
    """
    Indicates that configuration file couldn't be loaded for some reason, which is
    described by error causer or human-readable message
    """

    file_path: Optional[Path]
    """Source file path, or none if in-memory string used"""

    cause: Optional[Exception]
    """Cause of error (used instead of :py:attr:`__cause__` attribute)"""

    msg: Optional[str]
    """Optional error message"""

    def __init__(
        self, file_path: Optional[Path], cause: Exception = None, msg: str = None
    ):
        self.args = self.file_path, self.cause, self.msg = (file_path, cause, msg)

    def render_error(self) -> str:
        """
        Render error as a human-readable text

        :return: rendered text string
        """
        return f'{str(self.cause) if self.cause else self.msg}'

    def __str__(self) -> str:
        return f'{type(self).__name__}: {self.render_error()}'


class LoadingParseError(LoadingError):
    """
    Describes errors which occurs while parsing content of a configuration
    """

    def __init__(
        self,
        *args: Any,
        decoder: DecoderMeta = None,
        location: TextLocation = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.decoder = decoder

    def render_error(self) -> str:
        return (
            f'parsing error occurs while loading settings from '
            f'{_render_err_file_path(self.file_path)} using "{self.decoder.name} '
            f'loader": {str(self.cause)}'
        )


class LoadingValidationError(LoadingError, ValidationError):
    """
    Joins :py:class:`pydantic.ValidationError` and :py:class:`LoadingError`, primarily
    to allow catching specific for :py:func:`.load_settings` function errors at once
    """

    __slots__ = 'file_path', 'cause', 'msg'

    def __init__(
        self,
        raw_errors: Sequence[ErrorWrapper],
        model: Type[BaseModel],
        file_path: Optional[Path],
    ):
        ValidationError.__init__(self, raw_errors, model)
        super().__init__(file_path, None)

    def errors(self) -> List[Dict[str, Any]]:
        if self._error_cache is None:
            try:
                config = self.model.__config__  # type: ignore
            except AttributeError:
                config = self.model.__pydantic_model__.__config__  # type: ignore
            self._error_cache = serialize_errors(self, config)
        return self._error_cache

    def render_error(self) -> str:
        return render_validation_error(self)


class ExtendedErrorWrapper(ErrorWrapper):
    """
    Extends `pydantic.ErrorWrapper` adding additional fields which helps to locate
    bad filed value in configuration file or among environment variables
    """

    __slots__ = ('source_loc',)

    source_loc: AnySourceLoc
    """
    Describes source location, corresponding to :py:attr:`pydantic.ErrorWrapper.loc`
    """

    def __init__(
        self, exc: Exception, loc: ModelLoc, source_loc: AnySourceLoc = None,
    ):
        super().__init__(exc, tuple(loc))
        self.source_loc = source_loc

    def __repr_args__(self) -> Sequence[Tuple[Optional[str], Any]]:
        return list(super().__repr_args__()) + [('source_loc', self.source_loc)]


def _flatten_errors_wrappers(
    errors: Sequence[Any], *, loc: Optional[ModelLoc] = None
) -> Iterator[Tuple[ModelLoc, ErrorWrapper]]:
    """
    Iterate through ValidationError error wrappers reducing nesting
    """
    if loc is None:
        loc = ()
    for error in errors:
        if isinstance(error, ErrorWrapper):
            error_loc = tuple(loc) + error.loc_tuple()
            if isinstance(error.exc, ValidationError):
                yield from _flatten_errors_wrappers(error.exc.raw_errors, loc=error_loc)
            else:
                yield error_loc, error
        else:
            raise RuntimeError(f'Unknown error object: {error}')


def with_errs_locations(
    model: Type[BaseModel],
    validation_err: ValidationError,
    values_source: AnySourceLocProvider,
) -> ValidationError:
    def process_err_wrapper(
        err_wrapper: ErrorWrapper, loc_override: ModelLoc
    ) -> ErrorWrapper:
        try:
            location = values_source.get_location(loc_override)
        except KeyError:
            if isinstance(err_wrapper, ExtendedErrorWrapper):
                return ExtendedErrorWrapper(
                    err_wrapper.exc, loc_override, err_wrapper.source_loc
                )
            else:
                return ErrorWrapper(err_wrapper.exc, tuple(loc_override))

        return ExtendedErrorWrapper(err_wrapper.exc, loc_override, source_loc=location)

    return ValidationError(
        [
            process_err_wrapper(raw_err, model_loc)
            for model_loc, raw_err in _flatten_errors_wrappers(
                validation_err.raw_errors
            )
        ],
        model,
    )


def serialize_errors(err: ValidationError, config: Type[BaseConfig]) -> List[Json]:
    return [_ext_error_dict(err_wrapper, config) for err_wrapper in err.raw_errors]


def render_validation_error(error: LoadingValidationError) -> str:
    if issubclass(error.model, BaseModel):
        config = error.model.__config__
    else:
        config = error.model.__pydantic_model__.__config__

    errors = list(_flatten_errors_wrappers(error.raw_errors))
    errors_num = len(errors)

    rendered_errors = '\n'.join(
        _render_raw_error(raw_err, model_loc, config) for model_loc, raw_err in errors
    )
    env_used = any(
        not isinstance(raw_err.source_loc, TextLocation)
        for _, raw_err in errors
        if isinstance(raw_err, ExtendedErrorWrapper)
    )

    return (
        f'{errors_num} validation error{"" if errors_num == 1 else "s"} '
        f'for {error.model.__name__} '
        f'({_render_err_file_path(error.file_path)}'
        f"{' and environment variables' if env_used else ''}"
        f'):\n{rendered_errors}'
    )


def _render_err_file_path(file_path: Path) -> str:
    if file_path is not None:
        return f'configuration file at "{file_path}"'
    else:
        return 'in-memory buffer'


def _render_raw_error(
    raw_err: ErrorWrapper, loc_override: ModelLoc, config: Type[BaseConfig]
) -> str:
    serialized_err = cast(
        JsonDict, error_dict(raw_err.exc, config, tuple(loc_override))
    )
    return (
        f'{_render_err_loc(raw_err, loc_override)}\n'
        f'  {serialized_err["msg"]} ({_render_error_type_and_ctx(serialized_err)})'
    )


def _render_error_type_and_ctx(error: JsonDict) -> str:
    t = 'type=' + error['type']
    ctx = cast(JsonDict, error.get('ctx'))
    if ctx:
        return t + ''.join(f'; {k}={v}' for k, v in ctx.items())
    else:
        return t


def _render_err_loc(raw_err: ErrorWrapper, loc_override: ModelLoc) -> str:
    model_loc = ' -> '.join(str(loc) for loc in loc_override)
    if isinstance(raw_err, ExtendedErrorWrapper):
        if not isinstance(raw_err.source_loc, TextLocation):
            env_name, text_loc = raw_err.source_loc
            from_loc = f' from env "{env_name}"'
            if text_loc is not None:
                from_loc += f' at {text_loc.pos}:{text_loc.end_pos}'
        else:
            from_loc = (
                f' from file at {raw_err.source_loc.line}:{raw_err.source_loc.col}'
            )

        return model_loc + from_loc

    return model_loc


def _serialize_source_loc(loc: AnySourceLoc) -> Json:
    if isinstance(loc, TextLocation):
        return asdict(loc)

    assert (
        isinstance(loc, Sequence)
        and len(loc) == 2
        and (loc[1] is None or isinstance(loc[1], TextLocation))
    )

    env_name, text_loc = loc
    return [env_name, asdict(text_loc) if text_loc is not None else None]


def _ext_error_dict(err_wrapper: ErrorWrapper, config: Type[BaseConfig]) -> JsonDict:
    res = cast(JsonDict, error_dict(err_wrapper.exc, config, err_wrapper.loc_tuple()))
    if isinstance(err_wrapper, ExtendedErrorWrapper):
        res['source_loc'] = _serialize_source_loc(err_wrapper.source_loc)

    return res
