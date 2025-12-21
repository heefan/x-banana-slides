"""add result column to tasks table

Revision ID: 004_add_result
Revises: 38292967f3ca
Create Date: 2025-12-21 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '004_add_result'
down_revision = '38292967f3ca'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists"""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """
    Add result column to tasks table.
    
    Idempotent: checks if column exists before adding.
    """
    if not _column_exists('tasks', 'result'):
        op.add_column('tasks', sa.Column('result', sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists('tasks', 'result'):
        op.drop_column('tasks', 'result')

