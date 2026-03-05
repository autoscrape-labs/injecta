from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar, overload

T = TypeVar('T')


class Needs(Generic[T]):
    """Marker that declares a function parameter as a dependency to be injected.

    The return type of the dependency callable is preserved through the generic
    parameter `T`, enabling full type inference without explicit annotations.
    Supports both sync and async callables.

    Args:
        dependency: The callable (sync or async) that provides the dependency value.

    Example:
        ```python
        def get_db() -> Database:
            return Database()

        @inject
        def handler(db=Needs(get_db)):  # db is inferred as Database
            ...
        ```
    """

    __slots__ = ('dependency',)

    @overload
    def __init__(self, dependency: Callable[..., Awaitable[T]]) -> None: ...

    @overload
    def __init__(self, dependency: Callable[..., T]) -> None: ...

    def __init__(self, dependency: Callable[..., Any]) -> None:
        self.dependency = dependency

    def __repr__(self) -> str:
        name = getattr(self.dependency, '__name__', repr(self.dependency))
        return f'Needs({name})'
