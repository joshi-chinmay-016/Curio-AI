import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# -----------------------------------------------------------------------------
# Path Resolution
# -----------------------------------------------------------------------------
# Ensure project root is on sys.path so 'backend.app...' is resolvable
# from any working directory (e.g. repo root or backend directory).
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# -----------------------------------------------------------------------------
# Application Database & Model Imports
# -----------------------------------------------------------------------------
# Import application settings and Base with all 7 models registered:
# - User (users)
# - Session (sessions)
# - SessionState (session_states)
# - Message (messages)
# - TurnEvaluation (turn_evaluations)
# - Document (documents)
# - SessionReport (session_reports)
from backend.app.core.config import settings
from backend.app.db.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -----------------------------------------------------------------------------
# Dynamic Database URL Configuration
# -----------------------------------------------------------------------------
# Override sqlalchemy.url with dynamic database URL from settings.
# Supports targeting the isolated test database via '-x db=test' or ALEMBIC_TARGET_DB='test'.
# By default, targets the development database (DATABASE_URL).
x_args = context.get_x_argument(as_dictionary=True)
if x_args.get("db") == "test" or os.getenv("ALEMBIC_TARGET_DB") == "test":
    target_url = settings.get_test_database_url()
else:
    target_url = settings.get_database_url()

config.set_main_option("sqlalchemy.url", target_url)

# Set target_metadata for Alembic autogenerate support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
