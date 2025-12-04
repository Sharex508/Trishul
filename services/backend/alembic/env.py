from __future__ import annotations
import os
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Ensure project root is on sys.path so `import src` works when Alembic runs
ALEMBIC_DIR = Path(__file__).resolve().parent
APP_DIR = ALEMBIC_DIR.parent  # typically /app
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# import target metadata
from src.db import Base  # type: ignore
from src import models  # ensure models imported

target_metadata = Base.metadata


def _build_database_url() -> str:
    # Build DSN from environment to avoid hardcoding secrets in alembic.ini
    user = os.getenv("POSTGRES_USER", "crypto")
    password = os.getenv("POSTGRES_PASSWORD", "crypto")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "crypto")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    url = _build_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(_build_database_url(), poolclass=pool.NullPool)

    async with connectable.connect() as connection:  # type: ignore[call-arg]
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
