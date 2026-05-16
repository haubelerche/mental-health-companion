"""Fix session_summaries_archive.archive_id for SQLite autoincrement.

SQLite only gives autoincrement semantics to INTEGER PRIMARY KEY (not
BIGINT PRIMARY KEY). When the column is BIGINT, the NOT NULL constraint
fires on insert because no value is generated.

This migration recreates the table with the correct type in SQLite only;
PostgreSQL uses a server-side BIGSERIAL/sequence and is unaffected.

Revision ID: 0038_fix_archive_id_sqlite_autoincrement
Revises: 0037_ext_screening_legacy_cleanup
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op

revision = "0038_fix_archive_id_sqlite_autoincrement"
down_revision = "0037_ext_screening_legacy_cleanup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return  # PostgreSQL BIGSERIAL handles autoincrement correctly

    op.execute("""
        CREATE TABLE session_summaries_archive_new (
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
    op.execute("""
        INSERT INTO session_summaries_archive_new
            (archive_id, user_id, session_id, summary,
             session_started_at, dominant_emotion, sos_triggered, archived_at)
        SELECT
            rowid, user_id, session_id, summary,
            session_started_at, dominant_emotion, sos_triggered, archived_at
        FROM session_summaries_archive
    """)
    op.execute("DROP TABLE session_summaries_archive")
    op.execute(
        "ALTER TABLE session_summaries_archive_new RENAME TO session_summaries_archive"
    )


def downgrade() -> None:
    pass
