from __future__ import annotations

import sqlalchemy as sa
import enum

import sqlalchemy as sa
from sqlalchemy import String, Integer, DateTime, func, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(80), nullable=False, server_default="general")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="tool_tags",
        back_populates="tools",
        collection_class=list,
        lazy="selectin",
    )
    health: Mapped["ToolHealth"] = relationship("ToolHealth", back_populates="tool", uselist=False)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)

    tools: Mapped[list[Tool]] = relationship("Tool", secondary="tool_tags", back_populates="tags")


class ToolTag(Base):
    __tablename__ = "tool_tags"

    tool_id: Mapped[int] = mapped_column(
        Integer,
        sa.ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        sa.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "tool_id", name="uq_favorites_user_tool"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[int] = mapped_column(
        Integer,
        sa.ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolHealthStatus(str, enum.Enum):
    unknown = "unknown"
    up = "up"
    down = "down"


class ToolHealth(Base):
    __tablename__ = "tool_health"

    tool_id: Mapped[int] = mapped_column(
        Integer,
        sa.ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[ToolHealthStatus] = mapped_column(
        sa.Enum(ToolHealthStatus, name="tool_health_status"),
        nullable=False,
        server_default=ToolHealthStatus.unknown.value,
    )
    last_checked_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_error: Mapped[str] | None = mapped_column(String(512), nullable=True)

    tool: Mapped[Tool] = relationship("Tool", back_populates="health", uselist=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
