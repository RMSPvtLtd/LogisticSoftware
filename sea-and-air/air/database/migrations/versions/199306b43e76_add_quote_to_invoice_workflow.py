"""add quote to invoice workflow

Revision ID: 199306b43e76
Revises: b0627f6ddce6
Create Date: 2026-08-19 20:49:32.963275

Purely additive -- new Company/Invoice/InvoiceLineItem/InvoiceNumberCounter
tables, plus new nullable/defaulted columns on customer/inquiry/shipment/
quote. No batch_alter_table needed (see 7f3a9c4d1e20's docstring for why
that only matters for an ALTER COLUMN TYPE, which none of these are).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '199306b43e76'
down_revision: Union[str, Sequence[str], None] = 'b0627f6ddce6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# native_enum=False everywhere in this project (see models/_types.py::portable_enum).
CHARGE_KIND_ENUM = sa.Enum(
    'freight', 'documentation', 'customs', 'pickup', 'handling', 'other',
    name='chargekind', native_enum=False, length=30,
)
INVOICE_STATUS_ENUM = sa.Enum(
    'draft', 'issued', 'paid', 'cancelled', name='invoicestatus', native_enum=False, length=20,
)


def upgrade() -> None:
    op.add_column('customer', sa.Column('address', sa.Text(), nullable=True))

    op.add_column('inquiry', sa.Column('hs_code', sa.String(length=20), nullable=True))
    op.add_column('inquiry', sa.Column('pieces', sa.Integer(), nullable=True))
    op.add_column('inquiry', sa.Column('supplier_name', sa.String(length=200), nullable=True))
    op.add_column('inquiry', sa.Column('supplier_address', sa.Text(), nullable=True))

    op.add_column('shipment', sa.Column('carrier', sa.String(length=120), nullable=True))
    op.add_column('shipment', sa.Column('voyage_flight_number', sa.String(length=60), nullable=True))

    op.add_column('quote', sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False, server_default='0'))
    op.add_column('quote', sa.Column('discount_amount', sa.Numeric(12, 2), nullable=False, server_default='0'))

    op.create_table(
        'company',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=320), nullable=True),
        sa.Column('website', sa.String(length=200), nullable=True),
        sa.Column('tax_id_label', sa.String(length=60), nullable=True),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('company_reg_no', sa.String(length=100), nullable=True),
        sa.Column('bank_name', sa.String(length=200), nullable=True),
        sa.Column('bank_account_title', sa.String(length=200), nullable=True),
        sa.Column('bank_account_number', sa.String(length=100), nullable=True),
        sa.Column('bank_sort_code', sa.String(length=100), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'invoice_number_counter',
        sa.Column('year', sa.Integer(), primary_key=True),
        sa.Column('last_value', sa.Integer(), nullable=False),
    )

    op.create_table(
        'invoice',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_number', sa.String(length=40), nullable=False),
        sa.Column('quote_id', sa.Integer(), sa.ForeignKey('quote.id'), nullable=False),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('shipment.id'), nullable=False),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customer.id'), nullable=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('company.id'), nullable=False),
        sa.Column('status', INVOICE_STATUS_ENUM, nullable=False),
        sa.Column('issued_date', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('markup_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('discount_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('total', sa.Numeric(12, 2), nullable=False),
        sa.Column('customer_name_snapshot', sa.String(length=200), nullable=False),
        sa.Column('customer_address_snapshot', sa.Text(), nullable=True),
        sa.Column('supplier_name_snapshot', sa.String(length=200), nullable=True),
        sa.Column('supplier_address_snapshot', sa.Text(), nullable=True),
        sa.Column('origin_snapshot', sa.String(length=120), nullable=False),
        sa.Column('destination_snapshot', sa.String(length=120), nullable=False),
        sa.Column('mode_snapshot', sa.String(length=20), nullable=False),
        sa.Column('incoterm_snapshot', sa.String(length=10), nullable=False),
        sa.Column('hs_code_snapshot', sa.String(length=20), nullable=True),
        sa.Column('pieces_snapshot', sa.Integer(), nullable=True),
        sa.Column('weight_kg_snapshot', sa.Numeric(12, 3), nullable=False),
        sa.Column('volume_cbm_snapshot', sa.Numeric(12, 3), nullable=False),
        sa.Column('chargeable_weight_kg_snapshot', sa.Numeric(12, 3), nullable=False),
        sa.Column('carrier_snapshot', sa.String(length=120), nullable=True),
        sa.Column('voyage_flight_number_snapshot', sa.String(length=60), nullable=True),
        sa.Column('job_number_snapshot', sa.String(length=40), nullable=True),
        sa.Column('references_snapshot', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('quote_id', name='uq_invoice_quote_id'),
    )
    op.create_index('ix_invoice_invoice_number', 'invoice', ['invoice_number'], unique=True)
    op.create_index('ix_invoice_shipment_id', 'invoice', ['shipment_id'])
    op.create_index('ix_invoice_customer_id', 'invoice', ['customer_id'])

    op.create_table(
        'invoice_line_item',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoice.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', CHARGE_KIND_ENUM, nullable=False),
        sa.Column('description', sa.String(length=200), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 3), nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
    )
    op.create_index('ix_invoice_line_item_invoice_id', 'invoice_line_item', ['invoice_id'])


def downgrade() -> None:
    op.drop_index('ix_invoice_line_item_invoice_id', table_name='invoice_line_item')
    op.drop_table('invoice_line_item')

    op.drop_index('ix_invoice_customer_id', table_name='invoice')
    op.drop_index('ix_invoice_shipment_id', table_name='invoice')
    op.drop_index('ix_invoice_invoice_number', table_name='invoice')
    op.drop_table('invoice')

    op.drop_table('invoice_number_counter')
    op.drop_table('company')

    op.drop_column('quote', 'discount_amount')
    op.drop_column('quote', 'tax_amount')

    op.drop_column('shipment', 'voyage_flight_number')
    op.drop_column('shipment', 'carrier')

    op.drop_column('inquiry', 'supplier_address')
    op.drop_column('inquiry', 'supplier_name')
    op.drop_column('inquiry', 'pieces')
    op.drop_column('inquiry', 'hs_code')

    op.drop_column('customer', 'address')
