"""add quote carrier

Revision ID: 6e9611cb7afb
Revises: c4ef48af941b
Create Date: 2026-09-01 18:29:23.052596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e9611cb7afb'
down_revision: Union[str, Sequence[str], None] = 'c4ef48af941b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('quote', sa.Column('carrier', sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column('quote', 'carrier')
