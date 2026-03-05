from typing import Protocol

import pytest

from injecta import Container, Needs
from injecta.exceptions import InjectionError


class Database(Protocol):
    def query(self, sql: str) -> list[dict[str, str]]: ...


class Logger(Protocol):
    def info(self, msg: str) -> None: ...


class FakeDB:
    def query(self, sql: str) -> list[dict[str, str]]:
        return [{'sql': sql}]


class FakeLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, msg: str) -> None:
        self.messages.append(msg)


class TestContainerRegister:
    def test_register_instance_as_singleton(self) -> None:
        container = Container()
        db = FakeDB()
        container.register(Database, db)

        assert container.resolve(Database) is db

    def test_register_class_as_factory(self) -> None:
        container = Container()
        container.register(Database, FakeDB)

        first = container.resolve(Database)
        second = container.resolve(Database)

        assert isinstance(first, FakeDB)
        assert isinstance(second, FakeDB)
        assert first is not second

    def test_is_registered(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        assert container.is_registered(Database) is True
        assert container.is_registered(Logger) is False


class TestContainerResolve:
    def test_raises_on_unregistered_type(self) -> None:
        container = Container()

        with pytest.raises(InjectionError, match="No registration found for 'Database'"):
            container.resolve(Database)

    def test_singleton_returns_same_instance(self) -> None:
        container = Container()
        db = FakeDB()
        container.register(Database, db)

        assert container.resolve(Database) is container.resolve(Database)


class TestContainerInjectSync:
    def test_injects_registered_type(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        @container.inject
        def handler(db: Database) -> list[dict[str, str]]:
            return db.query('SELECT 1')

        assert handler() == [{'sql': 'SELECT 1'}]

    def test_injects_multiple_types(self) -> None:
        container = Container()
        db = FakeDB()
        logger = FakeLogger()
        container.register(Database, db)
        container.register(Logger, logger)

        @container.inject
        def handler(db: Database, logger: Logger, name: str) -> str:
            logger.info(f'Creating {name}')
            db.query(f'INSERT {name}')
            return name

        result = handler(name='John')

        assert result == 'John'
        assert logger.messages == ['Creating John']

    def test_skips_non_registered_params(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        @container.inject
        def handler(db: Database, name: str, count: int = 0) -> tuple[str, int]:
            return name, count

        result = handler(name='test', count=5)

        assert result == ('test', 5)

    def test_explicit_kwarg_overrides_injection(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        custom_db = FakeDB()

        @container.inject
        def handler(db: Database) -> Database:
            return db

        result = handler(db=custom_db)

        assert result is custom_db

    def test_supports_needs_alongside_container(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        def get_config() -> dict[str, bool]:
            return {'debug': True}

        @container.inject
        def handler(
            db: Database,
            config: dict[str, bool] = Needs(get_config),
        ) -> tuple[Database, dict[str, bool]]:
            return db, config

        db_result, config_result = handler()

        assert isinstance(db_result, FakeDB)
        assert config_result == {'debug': True}


class TestContainerInjectAsync:
    @pytest.mark.asyncio
    async def test_injects_registered_type(self) -> None:
        container = Container()
        container.register(Database, FakeDB())

        @container.inject
        async def handler(db: Database) -> list[dict[str, str]]:
            return db.query('SELECT 1')

        assert await handler() == [{'sql': 'SELECT 1'}]

    @pytest.mark.asyncio
    async def test_injects_multiple_types(self) -> None:
        container = Container()
        db = FakeDB()
        logger = FakeLogger()
        container.register(Database, db)
        container.register(Logger, logger)

        @container.inject
        async def handler(db: Database, logger: Logger, name: str) -> str:
            logger.info(f'Creating {name}')
            return name

        result = await handler(name='Jane')

        assert result == 'Jane'
        assert logger.messages == ['Creating Jane']

    @pytest.mark.asyncio
    async def test_explicit_kwarg_overrides_injection(self) -> None:
        container = Container()
        container.register(Database, FakeDB())
        custom_db = FakeDB()

        @container.inject
        async def handler(db: Database) -> Database:
            return db

        result = await handler(db=custom_db)

        assert result is custom_db
