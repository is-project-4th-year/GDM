"""Add missing columns to reports table

Revision ID: 13b15c589b23
Revises: 9141ea2da406
Create Date: 2025-11-15 13:51:24.597447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '13b15c589b23'
down_revision = '9141ea2da406'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to existing reports table
    op.add_column('reports', sa.Column('uuid', sa.String(length=36), nullable=True))
    op.add_column('reports', sa.Column('generated_by', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('report_type', sa.String(length=50), nullable=True))
    op.add_column('reports', sa.Column('title', sa.String(length=200), nullable=True))
    op.add_column('reports', sa.Column('pdf_filename', sa.String(length=255), nullable=True))
    op.add_column('reports', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('reports', sa.Column('generated_at', sa.DateTime(), nullable=True))
    op.add_column('reports', sa.Column('is_active', sa.Boolean(), nullable=True))
    
    # Update existing records with default values
    conn = op.get_bind()
    
    # Generate UUIDs for existing records
    conn.execute(sa.text("""
        UPDATE reports 
        SET uuid = lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', 1 + (abs(random()) % 4), 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))
        WHERE uuid IS NULL
    """))
    
    # Set default values for new columns
    conn.execute(sa.text("UPDATE reports SET report_type = 'risk_assessment' WHERE report_type IS NULL"))
    conn.execute(sa.text("UPDATE reports SET is_active = 1 WHERE is_active IS NULL"))
    conn.execute(sa.text("UPDATE reports SET title = 'Legacy Report' WHERE title IS NULL"))
    conn.execute(sa.text("UPDATE reports SET generated_at = created_at WHERE generated_at IS NULL"))


def downgrade():
    # Remove the columns we added
    op.drop_column('reports', 'is_active')
    op.drop_column('reports', 'generated_at')
    op.drop_column('reports', 'file_size')
    op.drop_column('reports', 'pdf_filename')
    op.drop_column('reports', 'title')
    op.drop_column('reports', 'report_type')
    op.drop_column('reports', 'generated_by')
    op.drop_column('reports', 'uuid')