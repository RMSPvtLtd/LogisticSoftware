"""add quote is_manual flag

Revision ID: 4a25908fa918
Revises: 6e9611cb7afb
Create Date: 2026-09-01 18:30:20.168422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a25908fa918'
down_revision: Union[str, Sequence[str], None] = '6e9611cb7afb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quote', sa.Column('is_manual', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('quote', 'is_manual')
