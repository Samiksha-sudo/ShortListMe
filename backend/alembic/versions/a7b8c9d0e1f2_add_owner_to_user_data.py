"""add user_id owner to cvs, job_descriptions, tailoring_jobs

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('cvs', 'job_descriptions', 'tailoring_jobs')


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column('user_id', sa.String(length=36), nullable=True))
            batch.create_index(f'ix_{table}_user_id', ['user_id'])
            batch.create_foreign_key(f'fk_{table}_user_id', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f'fk_{table}_user_id', type_='foreignkey')
            batch.drop_index(f'ix_{table}_user_id')
            batch.drop_column('user_id')
