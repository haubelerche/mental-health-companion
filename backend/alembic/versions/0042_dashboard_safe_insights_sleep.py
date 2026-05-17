"""Add sleep checkins and dashboard safe insights.

Revision ID: 0042_dashboard_safe_insights_sleep
Revises: 0041_chat_history_indexes
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0042_dashboard_safe_insights_sleep"
down_revision = "0041_chat_history_indexes"
branch_labels = None
depends_on = None


def _schema_name(bind: sa.engine.Connection) -> str | None:
    return "app" if bind.dialect.name == "postgresql" else None


def _has_table(bind: sa.engine.Connection, table_name: str) -> bool:
    if bind.dialect.name == "postgresql":
        return _relation_kind(bind, table_name) == "r"
    inspector = sa.inspect(bind)
    schema = _schema_name(bind)
    return table_name in inspector.get_table_names(schema=schema) or table_name in inspector.get_table_names()


def _relation_kind(bind: sa.engine.Connection, table_name: str) -> str | None:
    if bind.dialect.name != "postgresql":
        return None
    return bind.scalar(
        sa.text(
            """
            SELECT c.relkind
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = :table_name
              AND n.nspname IN ('app', current_schema())
            ORDER BY CASE WHEN n.nspname = 'app' THEN 0 ELSE 1 END
            LIMIT 1
            """
        ),
        {"table_name": table_name},
    )


def _drop_view_if_present(bind: sa.engine.Connection, table_name: str) -> None:
    if bind.dialect.name == "postgresql" and _relation_kind(bind, table_name) == "v":
        op.execute(sa.text(f"DROP VIEW IF EXISTS app.{table_name}"))


def _has_index(bind: sa.engine.Connection, table_name: str, index_name: str) -> bool:
    if bind.dialect.name == "postgresql":
        return bool(
            bind.scalar(
                sa.text("SELECT to_regclass(:qualified) IS NOT NULL OR to_regclass(:unqualified) IS NOT NULL"),
                {"qualified": f"app.{index_name}", "unqualified": index_name},
            )
        )
    inspector = sa.inspect(bind)
    schema = _schema_name(bind)
    indexes = inspector.get_indexes(table_name, schema=schema) if _has_table(bind, table_name) else []
    if not indexes and schema is not None:
        indexes = inspector.get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def _create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    if not _has_index(bind, table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_once(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    if _has_index(bind, table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    _drop_view_if_present(bind, "sleep_checkins")
    if not _has_table(bind, "sleep_checkins"):
        op.create_table(
            "sleep_checkins",
            sa.Column("sleep_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("sleep_date", sa.Date(), nullable=False),
            sa.Column("bedtime_at", sa.DateTime(), nullable=True),
            sa.Column("wake_time_at", sa.DateTime(), nullable=True),
            sa.Column("duration_hours", sa.Float(), nullable=True),
            sa.Column("sleep_quality", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("source", sa.String(20), nullable=False, server_default="self_report"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "sleep_date", name="uq_sleep_checkins_user_date"),
            sa.CheckConstraint("duration_hours IS NULL OR (duration_hours > 0 AND duration_hours <= 16)", name="ck_sleep_duration_hours"),
            sa.CheckConstraint("sleep_quality IS NULL OR (sleep_quality >= 1 AND sleep_quality <= 5)", name="ck_sleep_quality"),
            sa.CheckConstraint("source IN ('self_report','imported','system')", name="ck_sleep_checkins_source"),
        )
        _create_index_once("sleep_checkins", "idx_sleep_checkins_user_date", ["user_id", "sleep_date"])
    else:
        _create_index_once("sleep_checkins", "idx_sleep_checkins_user_date", ["user_id", "sleep_date"])

    _drop_view_if_present(bind, "dashboard_safe_insights")
    if not _has_table(bind, "dashboard_safe_insights"):
        op.create_table(
            "dashboard_safe_insights",
            sa.Column("insight_id", sa.String(50), primary_key=True),
            sa.Column("user_id", sa.String(50), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("category", sa.String(40), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("user_safe_summary", sa.Text(), nullable=False),
            sa.Column("interpretation", sa.Text(), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("evidence_window_start", sa.Date(), nullable=True),
            sa.Column("evidence_window_end", sa.Date(), nullable=True),
            sa.Column("confidence", sa.String(10), nullable=False),
            sa.Column("severity_band", sa.String(20), nullable=False),
            sa.Column("missing_data", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("recommended_actions", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("source_version", sa.String(80), nullable=False, server_default="dashboard_insight_builder_v1"),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "category", name="uq_dashboard_safe_insights_user_category"),
            sa.CheckConstraint(
                "category IN ('daily_mood','weekly_life_state','trigger_impact','sleep','nutrition','emotion','real_world_connection','self_care_action','screening','next_step')",
                name="ck_dashboard_safe_insights_category",
            ),
            sa.CheckConstraint("confidence IN ('low','medium','high')", name="ck_dashboard_safe_insights_confidence"),
            sa.CheckConstraint("severity_band IN ('neutral','watch')", name="ck_dashboard_safe_insights_severity"),
            sa.CheckConstraint("evidence_count >= 0", name="ck_dashboard_safe_insights_evidence_count"),
        )
        _create_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_category", ["user_id", "category"])
        _create_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_updated", ["user_id", "updated_at"])
    else:
        _create_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_category", ["user_id", "category"])
        _create_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_updated", ["user_id", "updated_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "dashboard_safe_insights"):
        _drop_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_updated")
        _drop_index_once("dashboard_safe_insights", "idx_dashboard_safe_insights_user_category")
        op.drop_table("dashboard_safe_insights")
    if _has_table(bind, "sleep_checkins"):
        _drop_index_once("sleep_checkins", "idx_sleep_checkins_user_date")
        op.drop_table("sleep_checkins")
