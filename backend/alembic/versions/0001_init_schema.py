"""initial schema

Revision ID: 0001_init_schema
Revises: 
Create Date: 2026-04-14 00:00:00
"""

from alembic import op

from app.services.db import models  # noqa: F401
from app.services.db.session import Base

# revision identifiers, used by Alembic.
revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
