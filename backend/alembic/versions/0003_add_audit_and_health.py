"""Add audit logs, favorites, tool health, and normalized tags

Revision ID: 0003_add_audit_and_health
Revises: 0002_add_tool_category_tags
Create Date: 2026-01-04 06:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_audit_and_health"
down_revision: Union[str, None] = "0002_add_tool_category_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_tools_tags_gin", table_name="tools")
    op.drop_column("tools", "tags")

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "tool_tags",
        sa.Column("tool_id", sa.Integer(), sa.ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_tool_tags_tool_id", "tool_tags", ["tool_id"])
    op.create_index("ix_tool_tags_tag_id", "tool_tags", ["tag_id"])

    op.create_table(
        "favorites",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tool_id", sa.Integer(), sa.ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorites_tool_id", "favorites", ["tool_id"])
    op.create_unique_constraint("uq_favorites_user_tool", "favorites", ["user_id", "tool_id"])

    tool_health_status = sa.Enum("unknown", "up", "down", name="tool_health_status", create_type=False)
    tool_health_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tool_health",
        sa.Column("tool_id", sa.Integer(), sa.ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", tool_health_status, nullable=False, server_default=sa.text("'unknown'::tool_health_status")),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("tool_health")
    sa.Enum("unknown", "up", "down", name="tool_health_status").drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("uq_favorites_user_tool", "favorites", type_="unique")
    op.drop_index("ix_favorites_tool_id", table_name="favorites")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_table("favorites")

    op.drop_index("ix_tool_tags_tag_id", table_name="tool_tags")
    op.drop_index("ix_tool_tags_tool_id", table_name="tool_tags")
    op.drop_table("tool_tags")

    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")

    op.add_column(
        "tools",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index("ix_tools_tags_gin", "tools", ["tags"], postgresql_using="gin")
