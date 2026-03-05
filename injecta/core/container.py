import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from injecta._wiring import build_injector
from injecta.core.needs import Needs
from injecta.exceptions import InjectionError
from injecta.resolution.resolver import resolve_dependencies

T = TypeVar('T')
P = ParamSpec('P')
R = TypeVar('R')


class Container:
    """Dependency injection container that resolves dependencies by type.

    Stores mappings from protocol/abstract types to their implementations.
    Instances are treated as singletons, classes/callables as factories
    that produce a new instance on each resolution.

    Example:
        ```python
        container = Container()
        container.register(Database, PostgresDB())
        container.register(Logger, ConsoleLogger)

        @container.inject
        def handler(db: Database, logger: Logger, name: str):
            ...

        handler(name="John")  # db and logger auto-injected
        ```
    """

    def __init__(self) -> None:
        self._singletons: dict[type[Any], Any] = {}
        self._factories: dict[type[Any], Callable[..., Any]] = {}

    def register(self, protocol: type[T], implementation: T | type[T]) -> None:
        """Register a dependency for a given type.

        If `implementation` is a class, it's treated as a factory (new instance
        per resolution). If it's an instance, it's treated as a singleton.

        Args:
            protocol: The type to register (typically a Protocol class).
            implementation: A concrete instance (singleton) or class (factory).
        """
        if isinstance(implementation, type):
            self._factories[protocol] = implementation
        else:
            self._singletons[protocol] = implementation

    def resolve(self, protocol: type[T]) -> T:
        """Resolve a dependency by its registered type.

        Args:
            protocol: The type to look up.

        Returns:
            The registered instance or a new instance from the factory.

        Raises:
            InjectionError: If no registration exists for the type.
        """
        if protocol in self._singletons:
            return self._singletons[protocol]  # type: ignore[return-value]

        if protocol in self._factories:
            return self._factories[protocol]()  # type: ignore[return-value]

        raise InjectionError(f"No registration found for '{protocol.__name__}'")

    def is_registered(self, protocol: type[Any]) -> bool:
        """Check if a type has been registered in this container."""
        return protocol in self._singletons or protocol in self._factories

    @overload
    def inject(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]: ...

    @overload
    def inject(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def inject(self, func: Callable[P, Any]) -> Callable[P, Any]:
        """Decorator that injects dependencies from this container.

        Resolves parameters by matching their type annotation against registered
        types. Also supports `Needs()` markers for factory-based injection.
        Parameters with no registration and no `Needs()` are left for the caller.

        Args:
            func: The function to decorate.

        Returns:
            A wrapper that auto-injects registered dependencies.

        Example:
            ```python
            @container.inject
            def handler(db: Database, name: str):
                ...

            handler(name="John")  # db resolved from container
            ```
        """
        dependant = resolve_dependencies(func)
        registered_params = self._resolve_registered_params(func)

        def container_resolver() -> dict[str, Any]:
            return {
                name: self.resolve(protocol)
                for name, protocol in registered_params.items()
            }

        return build_injector(func, dependant, container_resolver)

    def _resolve_registered_params(
        self, func: Callable[..., Any]
    ) -> dict[str, type[Any]]:
        params: dict[str, type[Any]] = {}
        signature = inspect.signature(func)

        for param_name, param in signature.parameters.items():
            if isinstance(param.default, Needs):
                continue

            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                continue

            if isinstance(annotation, type) and self.is_registered(annotation):
                params[param_name] = annotation

        return params
