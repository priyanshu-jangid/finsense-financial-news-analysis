"""add S&P 500 membership flag

Revision ID: 3fdce9473bf7
Revises: b3c9f2a1c123
Create Date: 2026-10-19 11:31:04.145311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fdce9473bf7'
down_revision: Union[str, Sequence[str], None] = 'b3c9f2a1c123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add S&P 500 membership flag to companies."""
    op.add_column(
        "companies",
        sa.Column(
            "is_sp500",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove S&P 500 membership flag."""
    op.drop_column("companies", "is_sp500")
