from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id",              sa.String(36),  nullable=False, primary_key=True),
        sa.Column("email",           sa.String(254), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("gpa_scale",       sa.String(16),  nullable=False, server_default="4.0"),
        sa.Column("university_name", sa.String(100), nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── guest_sessions ──
    op.create_table(
        "guest_sessions",
        sa.Column("session_id",  sa.String(36),  nullable=False, primary_key=True),
        sa.Column("calc_count",  sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                server_default=sa.func.now()),
        sa.Column("expires_at",  sa.DateTime(timezone=True), nullable=False),  # ← add this
    )

    # ── semesters ──
    op.create_table(
        "semesters",
        sa.Column("id",         sa.String(36),  nullable=False, primary_key=True),
        sa.Column("user_id",    sa.String(36),  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name",       sa.String(80),  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_semesters_user_id", "semesters", ["user_id"])

    # ── courses ──
    op.create_table(
        "courses",
        sa.Column("id",           sa.String(36),  nullable=False, primary_key=True),
        sa.Column("semester_id",  sa.String(36),  sa.ForeignKey("semesters.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name",         sa.String(120), nullable=True),
        sa.Column("credit_hours", sa.Float(),     nullable=False),
        sa.Column("grade",        sa.String(8),   nullable=False),
        sa.Column("grade_point",  sa.Float(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_courses_semester_id", "courses", ["semester_id"])

    # ── calculations ──
    op.create_table(
        "calculations",
        sa.Column("id",             sa.String(36),  nullable=False, primary_key=True),
        sa.Column("user_id",        sa.String(36),  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("session_id",     sa.String(36),  sa.ForeignKey("guest_sessions.session_id",
                  ondelete="SET NULL"), nullable=True),
        sa.Column("expression",     sa.Text(),      nullable=True),
        sa.Column("result",         sa.Float(),     nullable=True),
        sa.Column("scale_from",     sa.String(16),  nullable=True),
        sa.Column("scale_to",       sa.String(16),  nullable=True),
        sa.Column("classification", sa.String(20),  nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_calculations_user_id",    "calculations", ["user_id"])
    op.create_index("ix_calculations_session_id", "calculations", ["session_id"])
    op.create_index("ix_calculations_created_at", "calculations", ["created_at"])


def downgrade() -> None:
    op.drop_table("calculations")
    op.drop_table("courses")
    op.drop_table("semesters")
    op.drop_table("guest_sessions")
    op.drop_table("users")