"""
Pytest configuration and safe database fixtures for Curio AI backend.

These fixtures provide isolated, safe access to a dedicated test database
when running database integration tests.

Safety Invariants:
1. Never silently falls back to the application DATABASE_URL.
2. Rejects any database URL pointing to production or non-test databases.
3. Automatically masks credentials in logs, reprs, and failure reports.
4. Fails clearly when TEST_DATABASE_URL is not configured.
"""

import pytest
from typing import Generator


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "db_integration: Mark test as requiring a dedicated live PostgreSQL test database."
    )


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """
    Session fixture that retrieves and validates TEST_DATABASE_URL.
    Fails the test run clearly if a dedicated test database is not configured.
    """
    from backend.app.core.config import settings
    try:
        return settings.get_test_database_url()
    except (RuntimeError, ValueError) as e:
        pytest.fail(f"Test database configuration error: {e}")


@pytest.fixture(scope="session")
def test_db_engine(test_db_url):
    """
    Session fixture that creates a SQLAlchemy engine bound to the validated test database.
    Uses NullPool to ensure connections are closed promptly without holding pool locks.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    engine = create_engine(test_db_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator:
    """
    Function-scoped fixture providing an isolated database session.
    Uses an outer transaction and savepoints so tests can commit without
    persisting data to the physical database. Rolls back on teardown.
    """
    from sqlalchemy.orm import sessionmaker
    import backend.app.db.base  # Ensure all models are registered in mapper registry

    connection = test_db_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def override_get_db(test_db_session) -> Generator:
    """
    Function-scoped fixture that overrides FastAPI's get_db dependency
    with the isolated test session, cleaning up overrides on completion.
    """
    from backend.app.main import app
    from backend.app.db.session import get_db

    def _test_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _test_get_db
    try:
        yield test_db_session
    finally:
        app.dependency_overrides.pop(get_db, None)
