from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Tuple, Dict, Sequence, Union, Iterator, Iterable, cast

from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper

from pydantic_settings.loaders import Location, LoaderMeta


class LoadingError(ValueError):
    """
    Indicates that configuration file couldn't be loaded for some reason, which is described by error causer,
    human-readable message or set of another errors

    # TODO errors are still not representative, must be advanced or reworked
    """

    def __init__(
        self,
        file_path: Optional[Path],
        cause: Exception = None,
        msg: str = None,
        errs: Iterable[Exception] = None,
        content: str = None,
    ):
        self.args = self.file_path, self.cause, self.msg, self.errs, self.content = (
            file_path,
            cause,
            msg,
            errs,
            content,
        )


class LoadingParseError(LoadingError):
    """
    Describes errors which occurs while parsing content of a configuration
    """

    def __init__(
        self, *args: Any, loader: LoaderMeta, location: Location = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location


class LoadingValidationError(LoadingError, ValidationError):
    """
    Joins pydantic `ValidationError` and config loader error, primarily to allow
    catching either general load error or validation errors independently, when required
    """

    __slots__ = 'file_path', 'cause', 'msg', 'errs', 'content'

    def __init__(
        self,
        raw_errors: Sequence[ErrorWrapper],
        file_path: Optional[Path],
        content: str = None,
    ):
        ValidationError.__init__(self, raw_errors)
        super().__init__(file_path, self, content=content)

    def per_location_errors(self) -> Iterable[Tuple[Union[str, Location], Exception]]:
        return (
            (raw_err.env_loc or raw_err.text_loc, raw_err.exc)
            for raw_err in self.raw_errors
            if isinstance(raw_err, ExtendedErrorWrapper)
        )


class ExtendedErrorWrapper(ErrorWrapper):
    """
    Extends `pydantic.ErrorWrapper` adding additional fields which helps to locate
    bad filed value in configuration file or among environment variables
    """

    __slots__ = 'env_loc', 'text_loc', 'content'

    def __init__(
        self,
        *args: Any,
        env_loc: str = None,
        text_loc: Location = None,
        content: str = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.env_loc = env_loc
        self.text_loc = text_loc
        self.content = content

    @classmethod
    def from_error_wrapper(
        cls,
        err_wrapper: ErrorWrapper,
        *,
        env_loc: str = None,
        text_loc: Location = None,
    ) -> ExtendedErrorWrapper:
        """
        Alternative constructor trying to make copying faster
        """
        ext_wrappper = object.__new__(cls)
        for attr in err_wrapper.__slots__:
            setattr(ext_wrappper, attr, getattr(err_wrapper, attr))
        ext_wrappper.env_loc = env_loc
        ext_wrappper.text_loc = text_loc
        return ext_wrappper

    def dict(self, *, loc_prefix: Optional[Tuple[str, ...]] = None) -> Dict[str, Any]:
        d = super().dict(loc_prefix=loc_prefix)
        if self.env_loc is not None:
            d['env_loc'] = self.env_loc
        if self.text_loc is not None:
            d['text_loc'] = self.text_loc
        return d


def flatten_errors_wrappers(
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
                yield from flatten_errors_wrappers(error.exc.raw_errors, loc=error_loc)
            else:
                error.loc = error_loc
                yield error
        elif isinstance(error, list):
            yield from flatten_errors_wrappers(error)
        else:
            raise RuntimeError(f'Unknown error object: {error}')