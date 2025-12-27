"""Add branch_id to bookings, consultations, invoices

Revision ID: 003_add_branch_tracking
Revises: 002_add_content_management_tables
Create Date: 2025-12-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003_add_branch_tracking'
down_revision = '002_content_management'
branch_labels = None
depends_on = None

def upgrade():
    # Add branch_id to service_bookings
    op.add_column('service_bookings', sa.Column('branch_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_service_bookings_branch',
        'service_bookings',
        'branches',
        ['branch_id'],
        ['id']
    )
    
    # Add branch_id to consultations
    op.add_column('consultations', sa.Column('branch_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_consultations_branch',
        'consultations',
        'branches',
        ['branch_id'],
        ['id']
    )
    
    # Add branch_id to invoices (if table exists)
    try:
        op.add_column('invoices', sa.Column('branch_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_invoices_branch',
            'invoices',
            'branches',
            ['branch_id'],
            ['id']
        )
    except Exception:
        # Table might not exist yet
        pass

def downgrade():
    # Remove foreign keys and columns
    try:
        op.drop_constraint('fk_invoices_branch', 'invoices', type_='foreignkey')
        op.drop_column('invoices', 'branch_id')
    except Exception:
        pass
    
    op.drop_constraint('fk_consultations_branch', 'consultations', type_='foreignkey')
    op.drop_column('consultations', 'branch_id')
    
    op.drop_constraint('fk_service_bookings_branch', 'service_bookings', type_='foreignkey')
    op.drop_column('service_bookings', 'branch_id')
