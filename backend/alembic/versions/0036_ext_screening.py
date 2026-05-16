"""add extended screening tests

# Revision ID: 0036_ext_screening
# Revises: 0035_memory_text_dedup
# Create Date: 2026-05-15 10:20:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0036_ext_screening'
down_revision = '0035_memory_text_dedup'
branch_labels = None
depends_on = None

def upgrade():
    # Update ScreeningAnswer CheckConstraint
    # In PostgreSQL, we usually drop and recreate the constraint
    op.drop_constraint('ck_screening_answers_instrument', 'screening_answers', schema='app', type_='check')
    op.create_check_constraint(
        'ck_screening_answers_instrument',
        'screening_answers',
        "instrument_id IN ('phq9', 'gad7', 'dass21', 'mdq', 'pcl5')",
        schema='app'
    )

    # Add columns to ClinicalProfile
    op.add_column('clinical_profiles', sa.Column('dass21_depression_score', sa.Integer(), nullable=True), schema='app')
    op.add_column('clinical_profiles', sa.Column('dass21_anxiety_score', sa.Integer(), nullable=True), schema='app')
    op.add_column('clinical_profiles', sa.Column('dass21_stress_score', sa.Integer(), nullable=True), schema='app')
    op.add_column('clinical_profiles', sa.Column('mdq_score', sa.Integer(), nullable=True), schema='app')
    op.add_column('clinical_profiles', sa.Column('pcl5_score', sa.Integer(), nullable=True), schema='app')
    
    op.add_column('clinical_profiles', sa.Column('dass21_coverage', sa.JSON(), server_default='{}', nullable=False), schema='app')
    op.add_column('clinical_profiles', sa.Column('mdq_coverage', sa.JSON(), server_default='{}', nullable=False), schema='app')
    op.add_column('clinical_profiles', sa.Column('pcl5_coverage', sa.JSON(), server_default='{}', nullable=False), schema='app')

def downgrade():
    op.drop_column('clinical_profiles', 'pcl5_coverage', schema='app')
    op.drop_column('clinical_profiles', 'mdq_coverage', schema='app')
    op.drop_column('clinical_profiles', 'dass21_coverage', schema='app')
    op.drop_column('clinical_profiles', 'pcl5_score', schema='app')
    op.drop_column('clinical_profiles', 'mdq_score', schema='app')
    op.drop_column('clinical_profiles', 'dass21_stress_score', schema='app')
    op.drop_column('clinical_profiles', 'dass21_anxiety_score', schema='app')
    op.drop_column('clinical_profiles', 'dass21_depression_score', schema='app')

    op.drop_constraint('ck_screening_answers_instrument', 'screening_answers', schema='app', type_='check')
    op.create_check_constraint(
        'ck_screening_answers_instrument',
        'screening_answers',
        "instrument_id IN ('phq9', 'gad7')",
        schema='app'
    )
