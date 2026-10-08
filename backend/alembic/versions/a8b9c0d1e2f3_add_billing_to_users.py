"""add stripe customer and subscription status to users

Revision ID: a8b9c0d1e2f3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('stripe_customer_id', sa.String(length=64), nullable=True))
        batch.add_column(sa.Column('subscription_status', sa.String(length=32), nullable=True))
        batch.create_index('ix_users_stripe_customer_id', ['stripe_customer_id'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_index('ix_users_stripe_customer_id')
        batch.drop_column('subscription_status')
        batch.drop_column('stripe_customer_id')
