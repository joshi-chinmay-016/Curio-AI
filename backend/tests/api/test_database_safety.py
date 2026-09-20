"""
Unit tests for PostgreSQL test database configuration and safety invariants.

Validates that:
1. Passwords are automatically masked in URLs.
2. Test database URL is never silently defaulted to DATABASE_URL.
3. System and application databases cannot be targeted for testing.
4. Database names must explicitly contain 'test'.
5. Production hostnames and database names are rejected.
6. Unconfigured test database environments fail with clear actionable guidance.
"""

import pytest
from backend.app.core.config import settings


def test_mask_database_url_masks_password():
    """Verify that credentials in database URLs are cleanly masked."""
    raw_url = "postgresql://postgres:super_secret_123@localhost:5432/curio_test_db"
    masked = settings.mask_database_url(raw_url)
    assert "super_secret_123" not in masked
    assert "***" in masked
    assert "localhost:5432/curio_test_db" in masked


def test_mask_database_url_handles_empty_or_no_password():
    """Verify masking behaves safely with empty or passwordless URLs."""
    assert settings.mask_database_url("") == ""
    assert settings.mask_database_url("postgresql://localhost:5432/test_db") == "postgresql://localhost:5432/test_db"


def test_get_test_database_url_unconfigured_fails(monkeypatch):
    """Verify that an unconfigured or empty TEST_DATABASE_URL raises a clear RuntimeError."""
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setattr(settings, "TEST_DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="Dedicated test database is not configured"):
        settings.get_test_database_url()


def test_validate_test_database_url_rejects_identical_to_main():
    """Verify that using the main application database URL for testing is strictly rejected."""
    main_url = settings.get_database_url()
    with pytest.raises(ValueError, match="identical to the application DATABASE_URL"):
        settings.validate_test_database_url(main_url)


def test_validate_test_database_url_rejects_system_databases():
    """Verify that system databases like postgres or template1 are rejected."""
    for sys_db in ("postgres", "template1"):
        url = f"postgresql://postgres:postgres@localhost:5432/{sys_db}"
        with pytest.raises(ValueError, match="specifies system database"):
            settings.validate_test_database_url(url)


def test_validate_test_database_url_rejects_app_database():
    """Verify that the primary application database name is rejected."""
    url = f"postgresql://custom_user:custom_pass@localhost:5432/{settings.POSTGRES_DB}"
    with pytest.raises(ValueError, match="specifies application database"):
        settings.validate_test_database_url(url)


def test_validate_test_database_url_requires_test_in_name():
    """Verify that database names without 'test' are rejected to prevent accidental target of user databases."""
    url = "postgresql://postgres:postgres@localhost:5432/analytics_curio"
    with pytest.raises(ValueError, match="does not contain 'test'"):
        settings.validate_test_database_url(url)


def test_validate_test_database_url_rejects_production_keywords():
    """Verify that URLs containing production keywords are rejected."""
    prod_urls = [
        "postgresql://postgres:postgres@prod-db.curio.ai:5432/curio_test_db",
        "postgresql://postgres:postgres@localhost:5432/curio_test_production",
        "postgresql://postgres:postgres@live-server:5432/curio_test_db",
    ]
    for url in prod_urls:
        with pytest.raises(ValueError, match="contains production keyword"):
            settings.validate_test_database_url(url)


def test_validate_test_database_url_accepts_valid_test_url():
    """Verify that a compliant test database URL passes validation."""
    valid_url = "postgresql://postgres:postgres@localhost:5432/curio_test_db"
    result = settings.validate_test_database_url(valid_url)
    assert result == valid_url
