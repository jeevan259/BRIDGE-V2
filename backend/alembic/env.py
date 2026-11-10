"""Alembic environment configuration for async SQLAlchemy."""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so their metadata is populated
from app.models.base import Base  # noqa: F401
from app.models.organisation import Organisation  # noqa: F401
from app.models.user import User, RefreshToken  # noqa: F401
from app.models.knowledge import (  # noqa: F401
    KnowledgeSource, SourceVersion, Passage, KnowledgeItem, ItemVersion
)
from app.models.validation import (  # noqa: F401
    ValidationJob, Finding, FindingCitation, EvidenceReceipt
)
from app.models.continuity import (  # noqa: F401
    DependencyEdge, ChangeEvent, ImpactReport, RevalidationTask
)
from app.models.guideline import (  # noqa: F401
    ReviewSignal, AmbiguityAnalysis, GuidelineRecommendation
)
from app.models.audit import AuditEvent  # noqa: F401
import app.models  # noqa: F401
from app.models.job import Job  # noqa: F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override with environment variable if present
db_url = os.environ.get("DATABASE_URL") or os.environ.get(
    "DATABASE_SYNC_URL", "postgresql+asyncpg://bridge:bridge@localhost:5432/bridge"
)
# Async Alembic requires the asyncpg driver
if not db_url.startswith("postgresql+asyncpg://") and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
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
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode using run_sync."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
