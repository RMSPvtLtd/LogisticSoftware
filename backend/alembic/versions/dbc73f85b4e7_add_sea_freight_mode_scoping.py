"""add sea freight mode scoping

Revision ID: dbc73f85b4e7
Revises: 601b2d5be580
Create Date: 2026-08-12 00:00:00.000000

Adds `shipment.mode` (denormalized copy of `inquiry.mode`, backfilled from
it) so mode-aware queries -- the worker queue, the tracking checklist --
don't need a join through Inquiry on every read.

Adds `area.mode`, backfilled to 'AIR' for every existing area, and replaces
the old `UNIQUE(stage)` constraint with `UNIQUE(stage, mode)`. This is what
lets a sea Area own the same ShipmentStage value an air Area already owns
(e.g. both have an AIRWAY_BILL-stage area, one air one sea) without a
uniqueness conflict -- sea reuses the identical 17-stage pipeline air
already has, it just needs its own areas/worker queues per stage.

The old `UNIQUE(stage)` constraint on `area` was created unnamed
(see 37acfec25a45), which cannot be dropped by name in SQLite batch mode.
The `area` table is rebuilt from scratch instead (create new table with the
final schema, copy rows across with mode='AIR', drop old table, rename) --
this works identically on SQLite and PostgreSQL. `worker.area_id` keeps
pointing at the same ids since they're preserved across the rebuild.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'dbc73f85b4e7'
down_revision: Union[str, Sequence[str], None] = '601b2d5be580'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRANSPORT_MODE = sa.Enum('AIR', 'SEA', 'ROAD', name='transportmode', native_enum=False, length=30)

SHIPMENT_STAGE = sa.Enum(
    'inquiry', 'quotation', 'job_opening', 'airway_bill', 'gd', 'pickup',
    'gate_in', 'shipment_receipt', 'weighment', 'customs_examination',
    'customs_clearance', 'scanning', 'handover', 'departure', 'transhipment',
    'arrival', 'invoice_to_customer',
    name='shipmentstage', native_enum=False, length=30,
)


def upgrade() -> None:
    # --- shipment.mode ---
    with op.batch_alter_table('shipment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mode', TRANSPORT_MODE, nullable=True))

    op.execute(
        "UPDATE shipment SET mode = "
        "(SELECT inquiry.mode FROM inquiry WHERE inquiry.id = shipment.inquiry_id)"
    )

    with op.batch_alter_table('shipment', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('mode', existing_type=TRANSPORT_MODE, nullable=False)

    # --- area.mode + composite (stage, mode) uniqueness ---
    op.create_table(
        'area_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('stage', SHIPMENT_STAGE, nullable=False),
        sa.Column('mode', TRANSPORT_MODE, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stage', 'mode', name='uq_area_stage_mode'),
    )
    op.execute(
        "INSERT INTO area_new (id, name, stage, mode, created_at) "
        "SELECT id, name, stage, 'AIR', created_at FROM area"
    )
    op.drop_table('area')
    op.rename_table('area_new', 'area')


def downgrade() -> None:
    # Not supported -- see 7f3a9c4d1e20 for the same precedent (targets a
    # fresh/forward-only database).
    raise NotImplementedError("This migration cannot be downgraded automatically.")
