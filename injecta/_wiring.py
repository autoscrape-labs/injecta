import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, overload

from injecta.core.models import Dependant
from injecta.resolution.solver import solve_dependencies, solve_dependencies_sync

P = ParamSpec('P')
R = TypeVar('R')


@overload
def build_injector(
    func: Callable[P, Awaitable[R]],
    dependant: Dependant,
    extra_resolver: Callable[..., dict[str, Any]] | None = ...,
) -> Callable[P, Awaitable[R]]: ...


@overload
def build_injector(
    func: Callable[P, R],
    dependant: Dependant,
    extra_resolver: Callable[..., dict[str, Any]] | None = ...,
) -> Callable[P, R]: ...


def build_injector(
    func: Callable[P, Any],
    dependant: Dependant,
    extra_resolver: Callable[..., dict[str, Any]] | None = None,
) -> Callable[P, Any]:
    """Build a wrapper that injects dependencies into a function.

    Shared logic for both `@inject` and `@container.inject`. Handles
    sync/async detection, `Needs()` resolution, and optional extra
    resolution (e.g., container type lookups).

    Args:
        func: The function to wrap.
        dependant: Pre-analyzed dependency tree from the resolver.
        extra_resolver: Optional callable that returns additional
            param→value mappings (used by Container for type-based lookups).
    """
    has_needs = bool(dependant.dependencies)

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            if has_needs:
                needs_values = await solve_dependencies(dependant)
                for key, value in needs_values.items():
                    kwargs.setdefault(key, value)  # type: ignore[union-attr]

            if extra_resolver is not None:
                for key, value in extra_resolver().items():
                    if key not in kwargs:  # type: ignore[operator]
                        kwargs[key] = value  # type: ignore[index]

            return await func(*args, **kwargs)

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        if has_needs:
            needs_values = solve_dependencies_sync(dependant)
            for key, value in needs_values.items():
                kwargs.setdefault(key, value)  # type: ignore[union-attr]

        if extra_resolver is not None:
            for key, value in extra_resolver().items():
                if key not in kwargs:  # type: ignore[operator]
                    kwargs[key] = value  # type: ignore[index]

        return func(*args, **kwargs)

    return sync_wrapper
