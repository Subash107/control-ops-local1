"""Add tool category + tags

Revision ID: 0002_add_tool_category_tags
Revises: 0001_initial
Create Date: 2026-01-04 00:00:00

"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002_add_tool_category_tags"
down_revision: Union[str, None] = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tools",
        sa.Column("category", sa.String(length=80), nullable=False, server_default="general"),
    )
    op.add_column(
        "tools",
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # Optional indexes for faster filtering
    op.create_index("ix_tools_category", "tools", ["category"])
    op.create_index("ix_tools_tags_gin", "tools", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_tools_tags_gin", table_name="tools")
    op.drop_index("ix_tools_category", table_name="tools")
    op.drop_column("tools", "tags")
    op.drop_column("tools", "category")
