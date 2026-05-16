import sqlalchemy as sa
from alembic import op

"""Add extended screening fields.

Revision ID: 0036_ext_screening
Revises: 0035_memory_text_dedup
Create Date: 2026-05-15
"""

# revision identifiers, used by Alembic.
revision = "0036_ext_screening"
down_revision = "0035_memory_text_dedup"
branch_labels = None
depends_on = None


def _schema(bind: sa.engine.Connection) -> str | None:
    return None if bind.dialect.name == "sqlite" else "app"


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name, schema=_schema(bind)))


def _add_column_if_missing(bind: sa.engine.Connection, table_name: str, column: sa.Column) -> None:
    if _has_column(bind, table_name, column.name):
        return
    op.add_column(table_name, column, schema=_schema(bind))


def _replace_instrument_constraint(bind: sa.engine.Connection, allowed_values: tuple[str, ...]) -> None:
    values = ", ".join(f"'{value}'" for value in allowed_values)
    condition = f"instrument_id IN ({values})"
    if bind.dialect.name == "sqlite":
        return
    op.execute(sa.text("ALTER TABLE app.screening_answers DROP CONSTRAINT IF EXISTS ck_screening_answers_instrument"))
    op.create_check_constraint(
        "ck_screening_answers_instrument",
        "screening_answers",
        condition,
        schema="app",
    )


def upgrade() -> None:
    bind = op.get_bind()
    _replace_instrument_constraint(bind, ("phq9", "gad7", "dass21", "mdq", "pcl5"))

    _add_column_if_missing(bind, "clinical_profiles", sa.Column("dass21_depression_score", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("dass21_anxiety_score", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("dass21_stress_score", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("mdq_score", sa.Integer(), nullable=True))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("pcl5_score", sa.Integer(), nullable=True))

    _add_column_if_missing(bind, "clinical_profiles", sa.Column("dass21_coverage", sa.JSON(), server_default="{}", nullable=False))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("mdq_coverage", sa.JSON(), server_default="{}", nullable=False))
    _add_column_if_missing(bind, "clinical_profiles", sa.Column("pcl5_coverage", sa.JSON(), server_default="{}", nullable=False))


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema(bind)
    for column_name in (
        "pcl5_coverage",
        "mdq_coverage",
        "dass21_coverage",
        "pcl5_score",
        "mdq_score",
        "dass21_stress_score",
        "dass21_anxiety_score",
        "dass21_depression_score",
    ):
        if _has_column(bind, "clinical_profiles", column_name):
            op.drop_column("clinical_profiles", column_name, schema=schema)
    _replace_instrument_constraint(bind, ("phq9", "gad7"))
