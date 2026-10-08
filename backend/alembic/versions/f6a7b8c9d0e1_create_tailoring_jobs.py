"""create tailoring_jobs table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-03 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tailoring_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('cv_id', sa.String(length=36), nullable=False),
        sa.Column('jd_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('step', sa.String(length=16), nullable=False),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('tailoring_jobs')
