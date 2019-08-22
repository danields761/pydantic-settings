from pathlib import Path
from typing import Any, Optional, Tuple, Dict, Sequence, Union, Iterator, Iterable, List

from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper

from pydantic_settings.decoder import FileLocation, DecoderMeta
from pydantic_settings.types import SourceLocationProvider


class LoadingError(ValueError):
    """
    Indicates that configuration file couldn't be loaded for some reason, which is
    described by error causer, human-readable message or set of another errors
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
        return (
            f'error while loading settings from '
            f'{self._repr_file_path()}: {str(self.cause) if self.cause else self.msg}'
        )

    def __str__(self) -> str:
        return f'{type(self).__name__}: {self.render_error()}'

    def _repr_file_path(self) -> str:
        if self.file_path is not None:
            return f'configuration file at "{self.file_path}"'
        else:
            return 'in-memory configuration text'


class LoadingParseError(LoadingError):
    """
    Describes errors which occurs while parsing content of a configuration
    """

    def __init__(
        self,
        *args: Any,
        decoder: DecoderMeta = None,
        location: FileLocation = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.decoder = decoder

    def render_error(self) -> str:
        return (
            f'parsing error while loading settings from {self._repr_file_path()} '
            f'using "{self.decoder.name} loader": {str(self.cause)}'
        )


class LoadingValidationError(LoadingError, ValidationError):
    """
    Joins :py:class:`pydantic.ValidationError` and :py:class:`LoadingError`, primarily
    to allow catching specific for :py:func:`.load_settings` function errors at once
    """

    __slots__ = 'file_path', 'cause', 'msg'

    def __init__(self, raw_errors: Sequence[ErrorWrapper], file_path: Optional[Path]):
        ValidationError.__init__(self, raw_errors)
        super().__init__(file_path, None)

    def per_location_errors(
        self
    ) -> Iterable[Tuple[Union[str, FileLocation], Exception]]:
        return (
            (raw_err.source_loc, raw_err.exc)
            for raw_err in self.raw_errors
            if isinstance(raw_err, ExtendedErrorWrapper)
        )

    def render_error(self) -> str:
        env_used = any(
            raw_err.is_from_env
            for raw_err in self.raw_errors
            if isinstance(raw_err, ExtendedErrorWrapper)
        )
        nl = '\n'
        return (
            f'{len(self.raw_errors)} validation errors while loading settings '
            f'from {self._repr_file_path()}'
            f"{' and environment variables' if env_used else ''}"
            f""":\n{
                nl.join(
                    _render_raw_error(raw_err)
                    for raw_err in _flatten_errors_wrappers(self.raw_errors, loc=())
                )
            }"""
        )


def _render_raw_error(raw_err: ErrorWrapper) -> str:
    return (
        f'{_render_err_loc(raw_err)}\n'
        f'  {raw_err.msg} ({_display_error_type_and_ctx(raw_err)})'
    )


def _render_err_loc(raw_err: ErrorWrapper) -> str:
    model_loc = ' -> '.join(str(l) for l in raw_err.loc)
    if isinstance(raw_err, ExtendedErrorWrapper):
        if raw_err.is_from_env:
            from_loc = f' from env "{raw_err.source_loc}"'
        else:
            from_loc = (
                f' at {raw_err.source_loc.line} line '
                f'{raw_err.source_loc.end_pos} column'
            )
    else:
        from_loc = ''
    return model_loc + from_loc


def _display_error_type_and_ctx(error: ErrorWrapper) -> str:
    t = 'type=' + error.type_
    ctx = error.ctx
    if ctx:
        return t + ''.join(f'; {k}={v}' for k, v in ctx.items())
    else:
        return t


class ExtendedErrorWrapper(ErrorWrapper):
    """
    Extends `pydantic.ErrorWrapper` adding additional fields which helps to locate
    bad filed value in configuration file or among environment variables
    """

    __slots__ = ('source_loc',)

    source_loc: Union[str, FileLocation]
    """
    Describes source location, corresponding to :py:attr:`pydantic.ErrorWrapper.loc`
    """

    def __init__(
        self, *args: Any, source_loc: Union[str, FileLocation] = None, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.source_loc = source_loc

    @property
    def is_from_env(self) -> bool:
        """Is :py:attr:`source_loc` denotes environment variable name"""
        return isinstance(self.source_loc, str)

    @classmethod
    def from_error_wrapper(
        cls, err_wrapper: ErrorWrapper, *, source_loc: Union[str, FileLocation] = None
    ) -> 'ExtendedErrorWrapper':
        """
        Alternative constructor trying to make copying faster
        """
        ext_wrappper = object.__new__(cls)
        for attr in err_wrapper.__slots__:
            setattr(ext_wrappper, attr, getattr(err_wrapper, attr))
        ext_wrappper.source_loc = source_loc
        return ext_wrappper

    def dict(self, *, loc_prefix: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
        d = super().dict(loc_prefix=loc_prefix)
        d.update({'source_loc': self.source_loc, 'is_from_env': self.is_from_env})
        return d


def _flatten_errors_wrappers(
    errors: Sequence[Any], *, loc: Optional[Sequence[Union[str, int]]] = None
) -> Iterator[ErrorWrapper]:
    """
    Iterate through ValidationError error wrappers reducing nesting
    """
    if loc is None:
        loc = ()
    for error in errors:
        if isinstance(error, ErrorWrapper):
            error_loc = tuple(loc) + error.loc
            if isinstance(error.exc, ValidationError):
                yield from _flatten_errors_wrappers(error.exc.raw_errors, loc=error_loc)
            else:
                error.loc = error_loc
                yield error
        elif isinstance(error, list):
            yield from _flatten_errors_wrappers(error)
        else:
            raise RuntimeError(f'Unknown error object: {error}')


def with_errs_locations(
    validation_err: ValidationError,
    values_source: SourceLocationProvider[Union[str, FileLocation]],
) -> ValidationError:
    err_wrappers: List[ErrorWrapper] = []
    for raw_err in _flatten_errors_wrappers(validation_err.raw_errors):
        try:
            location = values_source.get_location(raw_err.loc)
            if isinstance(raw_err, ExtendedErrorWrapper):
                raw_err.source_loc = location
            else:
                raw_err = ExtendedErrorWrapper.from_error_wrapper(
                    raw_err, source_loc=location
                )
        except KeyError:
            pass

        err_wrappers.append(raw_err)

    return ValidationError(err_wrappers)
