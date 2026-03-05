from collections.abc import Callable
from typing import Any, TypeVar

from injecta.core.needs import Needs as NeedsMarker
from injecta.exceptions import InjectionError

T = TypeVar('T')


class Container:
    """Dependency injection container that resolves dependencies by type.

    Stores mappings from protocol/abstract types to their implementations.
    Instances are treated as singletons, classes/callables as factories
    that produce a new instance on each resolution.

    Use `container.Needs(Type)` to create a `Needs` marker bound to this
    container, then combine with `@inject` as usual.

    Example:
        ```python
        container = Container()
        container.register(Database, PostgresDB())
        container.register(Logger, ConsoleLogger)

        @inject
        def handler(
            db=container.Needs(Database),
            logger=container.Needs(Logger),
            name: str,
        ):
            ...

        handler(name="John")  # db and logger resolved from container
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

    def Needs(self, protocol: type[T]) -> NeedsMarker[T]:  # noqa: N802
        """Create a `Needs` marker bound to this container.

        Returns a `Needs` instance whose dependency resolves from this
        container by type. Works seamlessly with the `@inject` decorator.

        Args:
            protocol: The type to resolve from this container.

        Returns:
            A `Needs` marker that resolves `protocol` from this container.

        Example:
            ```python
            @inject
            def handler(db=container.Needs(Database)):
                db.query(...)
            ```
        """
        return NeedsMarker(lambda: self.resolve(protocol))
