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


@pytest.fixture(scope="function")
def create_test_user(test_db_session):
    """
    Factory fixture to dynamically create test users in the isolated test database.
    """
    import uuid
    from backend.app.models.user import User

    def _create_user(email: str = None, is_active: bool = True) -> User:
        user_email = email or f"test_user_{uuid.uuid4().hex[:8]}@curio.ai"
        user = User(email=user_email, is_active=is_active)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture(scope="function")
def test_user(create_test_user):
    """Function-scoped fixture providing a dynamically created test user."""
    return create_test_user()


@pytest.fixture(scope="function")
def test_token(test_user) -> str:
    """Function-scoped fixture providing a valid JWT for test_user."""
    from backend.app.core.security import create_access_token
    return create_access_token(subject=str(test_user.id))


@pytest.fixture(scope="function")
def auth_headers(test_token) -> dict:
    """Function-scoped fixture providing Authorization header for test_user."""
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture(scope="function")
def authenticated_client(override_get_db, test_user):
    """
    TestClient fixture bound to the isolated PostgreSQL test database session
    with a valid Bearer token for test_user.
    """
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.core.security import create_access_token

    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        client.headers.update(headers)
        # Attach user to client for test convenience
        client.user = test_user
        yield client
