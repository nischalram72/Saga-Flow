"""Add simulate_payment_failure

Revision ID: b1dfd6abd953
Revises: 05c86bbacedd
Create Date: 2026-08-10 02:11:29.718372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1dfd6abd953'
down_revision: Union[str, Sequence[str], None] = '05c86bbacedd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('saga_instances', sa.Column('simulate_payment_failure', sa.Boolean(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('saga_instances', 'simulate_payment_failure')
