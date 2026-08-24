"""production-hardening: ops auth, quote rejection/revisions, invoice
cancellation/replacement, shipment cancel/hold, document types

Revision ID: 90104ac8e3ed
Revises: 199306b43e76
Create Date: 2026-08-23 00:00:00.000000

Purely additive except one constraint swap on `invoice` (plain UNIQUE on
quote_id -> partial unique index on quote_id WHERE status <> 'CANCELLED',
so a cancelled invoice can be replaced by a new one for the same quote --
'CANCELLED' uppercase because every enum column in this project is
persisted by the Python Enum member's *name*, not its .value; see
models/_types.py::portable_enum). No enum-value migrations needed anywhere
-- every enum here is a plain VARCHAR (native_enum=False), so adding
QuoteStatus.REJECTED and the new DocumentType enum is a pure Python change
with nothing to migrate at the database level.

The two new self-referential FK columns (quote.root_quote_id,
invoice.replaces_invoice_id) and the invoice constraint swap go through
`batch_alter_table` -- SQLite can't ALTER a table to add/drop a constraint
directly, only via batch mode's copy-and-move strategy; on Postgres (this
app's actual runtime) `batch_alter_table` is a transparent passthrough to
plain ALTER TABLE, so this is free portability, not a behavior change.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90104ac8e3ed'
down_revision: Union[str, Sequence[str], None] = '199306b43e76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ops_user ---
    op.create_table(
        'ops_user',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('username', sa.String(length=60), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('username', name='uq_ops_user_username'),
    )
    op.create_index('ix_ops_user_username', 'ops_user', ['username'])

    # --- quote: rejection + revisioning ---
    op.add_column('quote', sa.Column('rejected_reason', sa.Text(), nullable=True))
    op.add_column('quote', sa.Column('rejected_by', sa.String(length=120), nullable=True))
    op.add_column('quote', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quote', sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('quote', sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('quote') as batch_op:
        batch_op.add_column(sa.Column('root_quote_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_quote_root_quote_id', 'quote', ['root_quote_id'], ['id'])
    op.create_index('ix_quote_root_quote_id', 'quote', ['root_quote_id'])

    # --- invoice: cancellation, replacement, payment-ready fields ---
    op.add_column('invoice', sa.Column('cancelled_reason', sa.Text(), nullable=True))
    op.add_column('invoice', sa.Column('cancelled_by', sa.String(length=120), nullable=True))
    op.add_column('invoice', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoice', sa.Column('payment_date', sa.Date(), nullable=True))
    op.add_column('invoice', sa.Column('amount_paid', sa.Numeric(12, 2), nullable=True))
    op.add_column('invoice', sa.Column('payment_method', sa.String(length=60), nullable=True))
    op.add_column('invoice', sa.Column('payment_reference', sa.String(length=120), nullable=True))

    # Replace the plain UNIQUE(quote_id) with a partial unique index (active
    # invoices only) -- what lets a replacement invoice exist for the same
    # quote once the original is cancelled, while still enforcing "at most
    # one active invoice per quote" at the database level.
    with op.batch_alter_table('invoice') as batch_op:
        batch_op.add_column(sa.Column('replaces_invoice_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_invoice_replaces_invoice_id', 'invoice', ['replaces_invoice_id'], ['id'])
        batch_op.drop_constraint('uq_invoice_quote_id', type_='unique')
    op.create_index('ix_invoice_replaces_invoice_id', 'invoice', ['replaces_invoice_id'])
    op.create_index('ix_invoice_quote_id', 'invoice', ['quote_id'])
    op.create_index(
        'uq_invoice_quote_id_active', 'invoice', ['quote_id'], unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
        sqlite_where=sa.text("status <> 'CANCELLED'"),
    )

    # --- shipment: cancellation + hold ---
    op.add_column('shipment', sa.Column('is_cancelled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('shipment', sa.Column('cancelled_reason', sa.Text(), nullable=True))
    op.add_column('shipment', sa.Column('customer_cancellation_note', sa.Text(), nullable=True))
    op.add_column('shipment', sa.Column('cancelled_by', sa.String(length=120), nullable=True))
    op.add_column('shipment', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shipment', sa.Column('is_on_hold', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('shipment', sa.Column('hold_reason', sa.Text(), nullable=True))
    op.add_column('shipment', sa.Column('hold_created_by', sa.String(length=120), nullable=True))
    op.add_column('shipment', sa.Column('hold_created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('shipment', sa.Column('hold_removed_by', sa.String(length=120), nullable=True))
    op.add_column('shipment', sa.Column('hold_removed_at', sa.DateTime(timezone=True), nullable=True))

    # --- shipment_document: document type classification ---
    document_type_enum = sa.Enum(
        'quotation', 'invoice', 'airway_bill', 'gd', 'customs', 'shipment_receipt',
        'examination', 'delivery', 'other',
        name='documenttype', native_enum=False, length=30,
    )
    op.add_column(
        'shipment_document',
        sa.Column('document_type', document_type_enum, nullable=False, server_default='other'),
    )


def downgrade() -> None:
    op.drop_column('shipment_document', 'document_type')

    op.drop_column('shipment', 'hold_removed_at')
    op.drop_column('shipment', 'hold_removed_by')
    op.drop_column('shipment', 'hold_created_at')
    op.drop_column('shipment', 'hold_created_by')
    op.drop_column('shipment', 'hold_reason')
    op.drop_column('shipment', 'is_on_hold')
    op.drop_column('shipment', 'cancelled_at')
    op.drop_column('shipment', 'cancelled_by')
    op.drop_column('shipment', 'customer_cancellation_note')
    op.drop_column('shipment', 'cancelled_reason')
    op.drop_column('shipment', 'is_cancelled')

    op.drop_index('uq_invoice_quote_id_active', table_name='invoice')
    op.drop_index('ix_invoice_quote_id', table_name='invoice')
    op.drop_index('ix_invoice_replaces_invoice_id', table_name='invoice')
    with op.batch_alter_table('invoice') as batch_op:
        batch_op.drop_constraint('fk_invoice_replaces_invoice_id', type_='foreignkey')
        batch_op.create_unique_constraint('uq_invoice_quote_id', ['quote_id'])
        batch_op.drop_column('replaces_invoice_id')
    op.drop_column('invoice', 'payment_reference')
    op.drop_column('invoice', 'payment_method')
    op.drop_column('invoice', 'amount_paid')
    op.drop_column('invoice', 'payment_date')
    op.drop_column('invoice', 'cancelled_at')
    op.drop_column('invoice', 'cancelled_by')
    op.drop_column('invoice', 'cancelled_reason')

    op.drop_index('ix_quote_root_quote_id', table_name='quote')
    with op.batch_alter_table('quote') as batch_op:
        batch_op.drop_constraint('fk_quote_root_quote_id', type_='foreignkey')
        batch_op.drop_column('root_quote_id')
    op.drop_column('quote', 'superseded_at')
    op.drop_column('quote', 'revision_number')
    op.drop_column('quote', 'rejected_at')
    op.drop_column('quote', 'rejected_by')
    op.drop_column('quote', 'rejected_reason')

    op.drop_index('ix_ops_user_username', table_name='ops_user')
    op.drop_table('ops_user')
