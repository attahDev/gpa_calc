"""Add lockout columns and full_name to users

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Brute-force lockout fields
    op.add_column("users", sa.Column(
        "failed_login_attempts", sa.Integer(), nullable=False, server_default="0"
    ))
    op.add_column("users", sa.Column(
        "locked_until", sa.DateTime(timezone=True), nullable=True
    ))

    # User display name (separate from university_name)
    op.add_column("users", sa.Column(
        "full_name", sa.String(150), nullable=True
    ))




def downgrade() -> None:
    op.drop_column("users", "full_name")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")