"""add cargo type snapshot to invoice

Revision ID: 2f37fcd64600
Revises: 90104ac8e3ed
Create Date: 2026-08-25 01:18:04.451826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f37fcd64600'
down_revision: Union[str, Sequence[str], None] = '90104ac8e3ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invoice', sa.Column('cargo_type_snapshot', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('invoice', 'cargo_type_snapshot')
