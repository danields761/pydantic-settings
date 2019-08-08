from typing import Sequence, Any, Optional, Tuple, Iterator, List, Union

from pydantic.error_wrappers import ErrorWrapper, ValidationError


def flatten_errors_wrappers(
    errors: Sequence[Any], *, loc: Optional[Tuple[Union[str, int]]] = None
) -> Iterator[ErrorWrapper]:
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
