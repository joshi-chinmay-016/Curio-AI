#!/bin/bash
set -e

# =============================================================================
# Curio AI - PostgreSQL Database Initialization Script
# =============================================================================
# This script is executed automatically by the PostgreSQL Docker container
# entrypoint ONLY during fresh database cluster creation (/docker-entrypoint-initdb.d/).
#
# Safety Guarantees:
# - Runs only when the postgres_data volume is freshly created and empty.
# - Non-destructive: Never drops, deletes, or alters existing databases or tables.
# - Idempotent: Safely skips creation if databases already exist.
# - Uses the configured POSTGRES_USER environment variable (default: postgres).
# - No hardcoded production credentials.
# =============================================================================

PG_USER="${POSTGRES_USER:-postgres}"

echo "Curio AI: Initializing databases with user '$PG_USER'..."

psql -v ON_ERROR_STOP=1 --username "$PG_USER" --dbname "postgres" <<-EOSQL
    SELECT 'CREATE DATABASE curio_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'curio_db')\gexec

    SELECT 'CREATE DATABASE curio_test_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'curio_test_db')\gexec

    GRANT ALL PRIVILEGES ON DATABASE curio_db TO "$PG_USER";
    GRANT ALL PRIVILEGES ON DATABASE curio_test_db TO "$PG_USER";
EOSQL

# Enable pgvector extension on both databases if available in the PostgreSQL image
echo "Curio AI: Enabling pgvector extension where available..."
psql -v ON_ERROR_STOP=0 --username "$PG_USER" --dbname "curio_db" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true
psql -v ON_ERROR_STOP=0 --username "$PG_USER" --dbname "curio_test_db" -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

echo "Curio AI: Both 'curio_db' and 'curio_test_db' are ready."
