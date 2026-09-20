import os
from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Curio AI"
    API_V1_STR: str = "/api/v1"
    
    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "curio_db"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str = ""
    # Test Database Configuration (Required only for live database integration tests)
    TEST_DATABASE_URL: str = ""

    # AI Keys
    GROQ_API_KEY: str = ""

    class Config:
        case_sensitive = True
        extra = "ignore"
        env_file = (
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
            str(Path(__file__).resolve().parent.parent.parent / ".env"),
            ".env",
            "backend/.env",
        )


    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @staticmethod
    def mask_database_url(url: str) -> str:
        """
        Safely mask credentials in a database URL for logging and error reporting.
        """
        if not url:
            return ""
        try:
            from sqlalchemy.engine import make_url
            parsed = make_url(url)
            return parsed.render_as_string(hide_password=True)
        except Exception:
            import re
            return re.sub(r":([^:@]+)@", r":***@", url)

    def validate_test_database_url(self, url: str) -> str:
        """
        Validates that a candidate test database URL is safe to use.
        Ensures:
        - URL is non-empty.
        - URL is not identical to the main application DATABASE_URL.
        - Database name is distinct from main POSTGRES_DB and system databases.
        - Database name explicitly contains 'test' (e.g. curio_test_db).
        - No production keywords appear in host or database name.
        """
        if not url or not url.strip():
            raise RuntimeError(
                "Dedicated test database is not configured. "
                "Please set TEST_DATABASE_URL (e.g., postgresql://postgres:postgres@localhost:5432/curio_test_db)."
            )

        url = url.strip()
        main_db_url = self.get_database_url().strip()
        if url == main_db_url:
            masked = self.mask_database_url(url)
            raise ValueError(
                f"Safety violation: TEST_DATABASE_URL ({masked}) is identical to the application DATABASE_URL. "
                "A dedicated, separate test database is strictly required."
            )

        try:
            from sqlalchemy.engine import make_url
            parsed = make_url(url)
        except Exception as e:
            raise ValueError(f"Invalid TEST_DATABASE_URL format: {e}")

        db_name = parsed.database
        if not db_name:
            raise ValueError("Safety violation: TEST_DATABASE_URL does not specify a target database name.")

        db_name_lower = db_name.lower()
        if db_name_lower in ("postgres", "template1"):
            raise ValueError(
                f"Safety violation: TEST_DATABASE_URL specifies system database '{db_name}'. "
                "A dedicated test database (e.g. 'curio_test_db') must be used."
            )

        if db_name_lower == self.POSTGRES_DB.lower():
            raise ValueError(
                f"Safety violation: TEST_DATABASE_URL specifies application database '{self.POSTGRES_DB}'. "
                "A dedicated test database (e.g. 'curio_test_db') must be used."
            )

        if "test" not in db_name_lower:
            raise ValueError(
                f"Safety violation: TEST_DATABASE_URL database name '{db_name}' does not contain 'test'. "
                "Database names for testing must contain 'test' (e.g. 'curio_test_db') to prevent accidental data loss."
            )

        host_lower = (parsed.host or "").lower()
        for keyword in ("prod", "production", "live"):
            if keyword in db_name_lower or keyword in host_lower:
                raise ValueError(
                    f"Safety violation: TEST_DATABASE_URL contains production keyword '{keyword}'. "
                    "Integration tests cannot be pointed to production environments."
                )

        return url

    def get_test_database_url(self) -> str:
        """
        Returns the validated TEST_DATABASE_URL.
        Fails if TEST_DATABASE_URL is not set or violates safety invariants.
        Never silently falls back to DATABASE_URL.
        """
        raw_url = self.TEST_DATABASE_URL or os.getenv("TEST_DATABASE_URL", "")
        return self.validate_test_database_url(raw_url)

settings = Settings()

