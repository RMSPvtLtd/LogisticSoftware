"""add quote clauses and invoice clauses snapshot

Revision ID: c4ef48af941b
Revises: 089801379c00
Create Date: 2026-09-01 18:05:16.473956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4ef48af941b'
down_revision: Union[str, Sequence[str], None] = '089801379c00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invoice', sa.Column('clauses_snapshot', sa.Text(), nullable=True))
    op.add_column('quote', sa.Column('clauses', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('quote', 'clauses')
    op.drop_column('invoice', 'clauses_snapshot')
