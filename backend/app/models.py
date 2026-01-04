from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import String, Integer, DateTime, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        sa.Index("ix_users_username", "username", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # admin | user
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tool(Base):
    __tablename__ = "tools"

    __table_args__ = (
        sa.Index("ix_tools_name", "name", unique=True),
        sa.Index("ix_tools_category", "category"),
        sa.Index("ix_tools_tags_gin", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    category: Mapped[str] = mapped_column(String(80), nullable=False, server_default="general")
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
    )

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
