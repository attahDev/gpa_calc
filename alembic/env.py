"""
alembic/env.py
--------------
Alembic migration environment.

Reads DATABASE_URL from the environment (never hardcoded).
Imports all models via backend.models so autogenerate can detect schema changes.

Usage:
    alembic upgrade head                                   # apply all migrations
    alembic downgrade -1                                   # roll back one
    alembic revision --autogenerate -m "add_foo_column"   # generate new migration
    alembic history                                        # list all migrations
    alembic current                                        # show current revision
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add the project root to sys.path so backend.* imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before importing anything that reads environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Base and all models so Alembic's autogenerate can see the schema.
# The noqa imports register models into Base.metadata.
from backend.database import Base  # noqa: E402
import backend.models               # noqa: F401, E402 — registers all models

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Set sqlalchemy.url from environment — never from the ini file
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData from our models — used for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Run migrations offline (no live DB connection needed)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Emit SQL to stdout without a live database connection.
    Useful for reviewing what a migration will do before applying it.

    Run with: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Run migrations online (with live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """
    Apply migrations against a live database.
    Uses NullPool so each migration run gets a fresh connection — consistent
    with how the app itself is configured.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()