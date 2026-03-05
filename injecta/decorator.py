from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from injecta._wiring import build_injector
from injecta.resolution.resolver import resolve_dependencies

P = ParamSpec('P')
R = TypeVar('R')


@overload
def inject(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]: ...


@overload
def inject(func: Callable[P, R]) -> Callable[P, R]: ...


def inject(func: Callable[P, Any]) -> Callable[P, Any]:
    """Decorator that resolves and injects dependencies marked with `Needs()`.

    Analyzes the function signature once at decoration time, then resolves
    all dependencies on each call. Supports both sync and async functions.

    Args:
        func: The function to decorate.

    Returns:
        A wrapper that auto-injects dependencies before calling the original function.

    Example:
        ```python
        @inject
        async def handler(db: Database = Needs(get_db)):
            ...
        ```
    """
    dependant = resolve_dependencies(func)
    return build_injector(func, dependant)
