"""Fix session_summaries_archive.archive_id autoincrement.

SQLite only gives autoincrement to INTEGER PRIMARY KEY (not BIGINT), so
every INSERT without an explicit archive_id raised NOT NULL constraint.

On PostgreSQL/Supabase the same symptom appears when the column has no
DEFAULT nextval(...) — which can happen if the table was created by a
raw CREATE TABLE (e.g. schema consolidation) instead of SQLAlchemy's
create_all() that would have emitted BIGSERIAL/sequence automatically.

This migration:
  - SQLite   : recreates the table with INTEGER PRIMARY KEY AUTOINCREMENT.
  - PostgreSQL: idempotently adds a sequence + DEFAULT if the column has
                no server default yet. Safe to run even if the sequence
                already exists.

Revision ID: 0038_fix_archive_id_sqlite_autoincrement
Revises: 0037_ext_screening_cleanup
Create Date: 2026-05-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_fix_archive_id_sqlite_autoincrement"
down_revision = "0037_ext_screening_cleanup"
branch_labels = None
depends_on = None

_SEQ = "session_summaries_archive_archive_id_seq"
_TABLE = "session_summaries_archive"


def _pg_archive_id_auto(bind: sa.engine.Connection) -> bool:
    """Return True if archive_id already auto-generates values.

    Covers two cases:
    - GENERATED ALWAYS/BY DEFAULT AS IDENTITY  (is_identity = 'YES')
    - DEFAULT nextval(...)                     (column_default is not null)
    """
    row = bind.execute(
        sa.text(
            """
            SELECT column_default, is_identity
            FROM information_schema.columns
            WHERE table_name = :tbl
              AND column_name = 'archive_id'
            LIMIT 1
            """
        ),
        {"tbl": _TABLE},
    ).fetchone()
    if row is None:
        return False
    column_default, is_identity = row
    return (column_default is not None) or (is_identity == "YES")


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "sqlite":
        op.execute(f"""
            CREATE TABLE {_TABLE}_new (
                archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR NOT NULL,
                session_id VARCHAR,
                summary JSON NOT NULL,
                session_started_at DATETIME,
                dominant_emotion VARCHAR,
                sos_triggered BOOLEAN NOT NULL DEFAULT 0,
                archived_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY(session_id) REFERENCES conversations (session_id) ON DELETE SET NULL
            )
        """)
        op.execute(f"""
            INSERT INTO {_TABLE}_new
                (archive_id, user_id, session_id, summary,
                 session_started_at, dominant_emotion, sos_triggered, archived_at)
            SELECT
                rowid, user_id, session_id, summary,
                session_started_at, dominant_emotion, sos_triggered, archived_at
            FROM {_TABLE}
        """)
        op.execute(f"DROP TABLE {_TABLE}")
        op.execute(f"ALTER TABLE {_TABLE}_new RENAME TO {_TABLE}")
        return

    # PostgreSQL / Supabase — add sequence + DEFAULT if missing.
    # Older environments created Alembic's version table with VARCHAR(32),
    # but this branch uses descriptive revision IDs longer than 32 chars.
    op.execute(sa.text("ALTER TABLE app.alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))

    if _pg_archive_id_auto(bind):
        return  # Already IDENTITY or nextval default — nothing to do.

    op.execute(sa.text(f"CREATE SEQUENCE IF NOT EXISTS {_SEQ}"))
    op.execute(
        sa.text(
            f"ALTER TABLE {_TABLE} "
            f"ALTER COLUMN archive_id SET DEFAULT nextval('{_SEQ}')"
        )
    )
    op.execute(
        sa.text(f"ALTER SEQUENCE {_SEQ} OWNED BY {_TABLE}.archive_id")
    )
    # Advance the sequence past any existing rows so the next INSERT gets a
    # fresh value and does not collide with manually-inserted rows.
    op.execute(
        sa.text(
            f"SELECT setval('{_SEQ}', COALESCE((SELECT MAX(archive_id) FROM {_TABLE}), 0) + 1, false)"
        )
    )


def downgrade() -> None:
    pass
