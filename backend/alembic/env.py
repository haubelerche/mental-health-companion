from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.core.config import get_settings
from app.services.db import models  # noqa: F401
from app.services.db.session import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.normalized_database_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    if connectable.dialect.name == "sqlite":
        # Match `get_engine()` — SQLite has no PG schemas; strip `app.*` qualification.
        connectable = connectable.execution_options(schema_translate_map={"app": None})

    with connectable.connect() as connection:
        configure_kw: dict[str, object] = {
            "connection": connection,
            "target_metadata": target_metadata,
            "compare_type": True,
        }
        if connection.dialect.name == "postgresql":
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            connection.execute(text("SET search_path TO app, extensions"))
            connection.commit()
            configure_kw["version_table_schema"] = "app"
        context.configure(**configure_kw)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
