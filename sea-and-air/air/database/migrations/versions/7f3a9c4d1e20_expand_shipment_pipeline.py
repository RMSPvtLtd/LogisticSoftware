"""expand shipment stages to the 17-step pipeline

Revision ID: 7f3a9c4d1e20
Revises: 37acfec25a45
Create Date: 2026-08-11 00:00:00.000000

Shipment.quote_id and job_number become nullable -- a shipment now exists
from the moment an Inquiry is filed (services.inquiries.create_inquiry),
before a quote is generated or accepted, so both are only populated once
their respective stage is reached. shipment.inquiry_id becomes unique -- a
Shipment is now created exactly once per Inquiry, never more.

The stage vocabulary itself is a breaking change (docs_filed/in_transit/
arrived/... don't map one-to-one onto the new 17-stage pipeline), so this
migration does not attempt to remap existing stage data. It targets an
empty/fresh database. `recreate='always'` forces the CHECK constraint
backing each portable enum column to be rebuilt from the current Python
enum on both SQLite and PostgreSQL, rather than relying on a plain
ALTER COLUMN to update it (which does not reliably touch CHECK constraints).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7f3a9c4d1e20'
down_revision: Union[str, Sequence[str], None] = '37acfec25a45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_SHIPMENT_STAGE = sa.Enum(
    'inquiry', 'quotation', 'job_opening', 'airway_bill', 'gd', 'pickup',
    'gate_in', 'shipment_receipt', 'weighment', 'customs_examination',
    'customs_clearance', 'scanning', 'handover', 'departure', 'transhipment',
    'arrival', 'invoice_to_customer',
    name='shipmentstage', native_enum=False, length=30,
)

OLD_SHIPMENT_STAGE = sa.Enum(
    'inquiry', 'quoted', 'job_opened', 'docs_filed', 'picked_up', 'in_transit',
    'customs_clearance', 'arrived', 'delivered',
    name='shipmentstage', native_enum=False, length=30,
)


def upgrade() -> None:
    with op.batch_alter_table('shipment', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('quote_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('job_number', existing_type=sa.String(length=40), nullable=True)
        batch_op.alter_column('stage', existing_type=OLD_SHIPMENT_STAGE, type_=NEW_SHIPMENT_STAGE, nullable=False)
        batch_op.create_unique_constraint('uq_shipment_inquiry_id', ['inquiry_id'])

    with op.batch_alter_table('status_event', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('stage', existing_type=OLD_SHIPMENT_STAGE, type_=NEW_SHIPMENT_STAGE, nullable=False)

    with op.batch_alter_table('area', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('stage', existing_type=OLD_SHIPMENT_STAGE, type_=NEW_SHIPMENT_STAGE, nullable=False)


def downgrade() -> None:
    # Not supported -- the stage vocabulary changed in a way that doesn't
    # map back cleanly (docs_filed/in_transit/arrived/... no longer exist).
    raise NotImplementedError("This migration cannot be downgraded automatically.")
