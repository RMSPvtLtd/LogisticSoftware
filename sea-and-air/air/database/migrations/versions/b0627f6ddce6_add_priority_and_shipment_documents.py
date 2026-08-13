"""add priority and shipment documents

Revision ID: b0627f6ddce6
Revises: 601b2d5be580
Create Date: 2026-08-13 23:39:20.429519

Purely additive -- one new column (with a server_default so existing rows
backfill cleanly) and one new table, both plain VARCHAR/bytea, no
batch_alter_table needed (see 7f3a9c4d1e20's docstring for why that only
matters for an ALTER COLUMN TYPE, which neither of these is).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0627f6ddce6'
down_revision: Union[str, Sequence[str], None] = '601b2d5be580'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# native_enum=False everywhere in this project (see models/_types.py::portable_enum)
# -- these are plain VARCHAR columns, not real Postgres enum types.
PRIORITY_ENUM = sa.Enum('low', 'medium', 'high', name='priority', native_enum=False, length=30)

SHIPMENT_STAGE_ENUM = sa.Enum(
    'inquiry', 'quotation', 'job_opening', 'airway_bill', 'pickup', 'gate_in',
    'shipment_receipt', 'weighment', 'gd', 'customs_examination', 'customs_clearance',
    'scanning', 'handover', 'departure', 'transhipment', 'arrival', 'invoice_to_customer',
    name='shipmentstage', native_enum=False, length=30,
)


def upgrade() -> None:
    op.add_column(
        'shipment',
        sa.Column('priority', PRIORITY_ENUM, nullable=False, server_default='medium'),
    )

    op.create_table(
        'shipment_document',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('shipment.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', SHIPMENT_STAGE_ENUM, nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('uploaded_by', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_shipment_document_shipment_id', 'shipment_document', ['shipment_id'])


def downgrade() -> None:
    op.drop_index('ix_shipment_document_shipment_id', table_name='shipment_document')
    op.drop_table('shipment_document')
    op.drop_column('shipment', 'priority')
