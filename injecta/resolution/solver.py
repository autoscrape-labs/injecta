import inspect
from collections.abc import Callable
from typing import Any

from injecta.core.models import Dependant
from injecta.exceptions import InjectionError


async def solve_dependencies(
    dependant: Dependant,
    _cache: dict[Callable[..., Any], Any] | None = None,
) -> dict[str, Any]:
    """Resolve a dependency tree asynchronously, executing each dependency.

    Traverses the tree depth-first, resolving sub-dependencies before their
    parents. Supports both sync and async callables. Identical callables
    appearing in multiple branches are executed only once per resolution
    cycle (diamond dependency deduplication).

    Args:
        dependant: The root of the dependency tree to resolve.

    Returns:
        A mapping of parameter names to their resolved values.
    """
    if _cache is None:
        _cache = {}

    values: dict[str, Any] = {}

    for sub_dep in dependant.dependencies:
        if sub_dep.call in _cache:
            values[sub_dep.param_name] = _cache[sub_dep.call]
            continue

        sub_values = await solve_dependencies(sub_dep, _cache)
        result = await _execute(sub_dep.call, sub_values)
        _cache[sub_dep.call] = result
        values[sub_dep.param_name] = result

    return values


def solve_dependencies_sync(
    dependant: Dependant,
    _cache: dict[Callable[..., Any], Any] | None = None,
) -> dict[str, Any]:
    """Resolve a dependency tree synchronously.

    Same as `solve_dependencies` but only supports sync callables.
    Raises `InjectionError` if an async dependency is encountered.

    Args:
        dependant: The root of the dependency tree to resolve.

    Returns:
        A mapping of parameter names to their resolved values.

    Raises:
        InjectionError: If an async callable is found in the tree.
    """
    if _cache is None:
        _cache = {}

    values: dict[str, Any] = {}

    for sub_dep in dependant.dependencies:
        if inspect.iscoroutinefunction(sub_dep.call):
            raise InjectionError(
                f"Cannot use async dependency '{sub_dep.call.__name__}' in sync context. "
                f"Use an async function with @inject instead."
            )

        if sub_dep.call in _cache:
            values[sub_dep.param_name] = _cache[sub_dep.call]
            continue

        sub_values = solve_dependencies_sync(sub_dep, _cache)
        result = sub_dep.call(**sub_values)
        _cache[sub_dep.call] = result
        values[sub_dep.param_name] = result

    return values


async def _execute(call: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
    if inspect.iscoroutinefunction(call):
        return await call(**kwargs)
    return call(**kwargs)
