"""add airline schedule table

Revision ID: 089801379c00
Revises: 2f37fcd64600
Create Date: 2026-09-01 17:49:31.473969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '089801379c00'
down_revision: Union[str, Sequence[str], None] = '2f37fcd64600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'airline_schedule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('airline_name', sa.String(length=120), nullable=False),
        sa.Column('origin', sa.String(length=120), nullable=False),
        sa.Column('destination', sa.String(length=120), nullable=False),
        sa.Column('mode', sa.Enum('AIR', 'SEA', 'ROAD', name='transportmode', native_enum=False, length=30), nullable=False),
        sa.Column('days_of_week', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('airline_schedule')
