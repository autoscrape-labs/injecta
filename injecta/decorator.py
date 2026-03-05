import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, overload

from injecta.resolution.resolver import resolve_dependencies
from injecta.resolution.solver import solve_dependencies, solve_dependencies_sync

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

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            dep_values = await solve_dependencies(dependant)
            for key, value in dep_values.items():
                kwargs.setdefault(key, value)  # type: ignore[union-attr]
            return await func(*args, **kwargs)

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        dep_values = solve_dependencies_sync(dependant)
        for key, value in dep_values.items():
            kwargs.setdefault(key, value)  # type: ignore[union-attr]
        return func(*args, **kwargs)

    return sync_wrapper
