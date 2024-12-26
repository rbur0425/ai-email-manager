"""add_confidence_to_processing_history

Revision ID: 65f3ec1eb29a
Revises: 
Create Date: 2024-12-26 14:57:15.167957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65f3ec1eb29a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add confidence column to processing_history table
    op.add_column('processing_history',
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0')
    )


def downgrade() -> None:
    # Remove confidence column from processing_history table
    op.drop_column('processing_history', 'confidence')
