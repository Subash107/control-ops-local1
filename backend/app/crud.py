from __future__ import annotations

import datetime
import time

import httpx
from fastapi import Request
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    AuditLog,
    Favorite,
    Tag,
    Tool,
    ToolTag,
    ToolHealth,
    ToolHealthStatus,
    User,
)
from .security import hash_password


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def create_user(db: Session, username: str, password: str, role: str) -> User:
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, password: str | None, role: str | None) -> User:
    if password:
        user.password_hash = hash_password(password)
    if role:
        user.role = role
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    stmt = select(User).order_by(User.id)
    return list(db.scalars(stmt).all())


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def _tool_sort_column(field: str) -> Tool | func.ColumnElement:
    return {
        "name": Tool.name,
        "category": Tool.category,
        "created_at": Tool.created_at,
    }.get(field.lower(), Tool.created_at)


def _normalize_tag_values(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen = set()
    for raw in tags:
        if raw is None:
            continue
        value = raw.strip().lower()
        if not value:
            continue
        if value in seen:
            continue
        if len(normalized) >= 20:
            raise ValueError("A tool may have at most 20 tags")
        seen.add(value)
        normalized.append(value[:80])
    return normalized


def _resolve_tags(db: Session, tags: list[str]) -> list[Tag]:
    normalized = _normalize_tag_values(tags)
    if not normalized:
        return []
    existing = {tag.name: tag for tag in db.scalars(select(Tag).where(Tag.name.in_(normalized))).all()}
    result: list[Tag] = []
    for name in normalized:
        tag = existing.get(name)
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
            existing[name] = tag
        result.append(tag)
    return result


def _apply_tool_filters(stmt, category: str | None, search: str | None, tag: str | None):
    if category:
        stmt = stmt.where(func.lower(Tool.category) == category.strip().lower())

    if search:
        query = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Tool.name).like(query),
                func.lower(Tool.description).like(query),
            )
        )

    if tag:
        tag_value = tag.strip().lower()
        if tag_value:
            subq = select(ToolTag.tool_id).join(Tag).where(Tag.name == tag_value)
            stmt = stmt.where(Tool.id.in_(subq))

    return stmt


def list_tools(
    db: Session,
    *,
    category: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    sort_spec: list[tuple[str, str]] | None = None,
) -> list[Tool]:
    stmt = select(Tool).options(selectinload(Tool.tags))
    order_by = []

    if sort_spec:
        for field, direction in sort_spec:
            col = _tool_sort_column(field)
            order_by.append(col.asc() if direction.lower() == "asc" else col.desc())
    else:
        col = _tool_sort_column(sort_by)
        order_by.append(col.asc() if sort_dir.lower() == "asc" else col.desc())

    order_by.append(Tool.id.desc())

    stmt = _apply_tool_filters(stmt, category=category, search=search, tag=tag)
    stmt = stmt.order_by(*order_by).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_tools(db: Session, *, category: str | None = None, tag: str | None = None, search: str | None = None) -> int:
    stmt = select(func.count(distinct(Tool.id))).select_from(Tool)
    stmt = _apply_tool_filters(stmt, category=category, search=search, tag=tag)
    return int(db.scalar(stmt) or 0)


def list_tool_categories(db: Session) -> list[str]:
    stmt = select(Tool.category).distinct().order_by(Tool.category)
    return [category for category in db.scalars(stmt).all() if category]


def list_tool_tags(db: Session) -> list[str]:
    stmt = select(Tag.name).order_by(Tag.name)
    return [name for name in db.scalars(stmt).all() if name]


class DuplicateNameError(Exception):
    pass


def _normalize_tool_url(url: str | None) -> str | None:
    return url.strip() if url else url


def create_tool(
    db: Session,
    name: str,
    description: str,
    url: str,
    category: str,
    tags: list[str],
) -> Tool:
    tag_objs = _resolve_tags(db, tags)
    tool = Tool(
        name=name.strip(),
        description=description,
        url=_normalize_tool_url(url) or "",
        category=category.strip() or "general",
    )
    tool.tags = tag_objs
    db.add(tool)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        lowered = str(exc).lower()
        if "unique constraint" in lowered or "duplicate key" in lowered or "ix_tools_name" in lowered:
            raise DuplicateNameError("Tool name already exists") from exc
        raise
    db.refresh(tool)
    return tool


def update_tool(
    db: Session,
    tool: Tool,
    name: str | None,
    description: str | None,
    url: str | None,
    category: str | None,
    tags: list[str] | None,
) -> Tool:
    if name is not None:
        tool.name = name.strip()
    if description is not None:
        tool.description = description
    if url is not None:
        tool.url = _normalize_tool_url(url) or ""
    if category is not None:
        tool.category = category.strip() or "general"
    if tags is not None:
        tool.tags = _resolve_tags(db, tags)

    db.add(tool)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        lowered = str(exc).lower()
        if "unique constraint" in lowered or "duplicate key" in lowered or "ix_tools_name" in lowered:
            raise DuplicateNameError("Tool name already exists") from exc
        raise
    db.refresh(tool)
    return tool


def delete_tool(db: Session, tool: Tool) -> None:
    db.delete(tool)
    db.commit()


def get_tool_by_id(db: Session, tool_id: int) -> Tool | None:
    stmt = select(Tool).options(selectinload(Tool.tags)).where(Tool.id == tool_id)
    return db.scalar(stmt)


def tool_to_dict(tool: Tool) -> dict:
    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "url": tool.url,
        "category": tool.category,
        "tags": [tag.name for tag in tool.tags],
        "created_at": tool.created_at.isoformat() if tool.created_at else None,
    }


def add_favorite(db: Session, user_id: int, tool_id: int) -> None:
    exists = db.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.tool_id == tool_id))
    if exists:
        return
    fav = Favorite(user_id=user_id, tool_id=tool_id)
    db.add(fav)
    db.commit()


def remove_favorite(db: Session, user_id: int, tool_id: int) -> None:
    fav = db.scalar(select(Favorite).where(Favorite.user_id == user_id, Favorite.tool_id == tool_id))
    if not fav:
        return
    db.delete(fav)
    db.commit()


def count_user_favorites(db: Session, user_id: int) -> int:
    stmt = select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
    return int(db.scalar(stmt) or 0)


def list_user_favorites(db: Session, user_id: int, limit: int, offset: int) -> list[Tool]:
    stmt = (
        select(Tool)
        .options(selectinload(Tool.tags))
        .join(Favorite, Favorite.tool_id == Tool.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


def get_tool_health(db: Session, tool_id: int) -> ToolHealth | None:
    return db.get(ToolHealth, tool_id)


def _create_or_refresh_health(
    db: Session,
    tool_id: int,
    status: ToolHealthStatus,
    latency_ms: float | None,
    last_error: str | None,
) -> ToolHealth:
    now = datetime.datetime.now(datetime.timezone.utc)
    health = db.get(ToolHealth, tool_id)
    if not health:
        health = ToolHealth(
            tool_id=tool_id,
            status=status,
            last_checked_at=now,
            latency_ms=latency_ms,
            last_error=last_error,
        )
    else:
        health.status = status
        health.last_checked_at = now
        health.latency_ms = latency_ms
        health.last_error = last_error

    db.add(health)
    db.commit()
    db.refresh(health)
    return health


def _check_tool_url(url: str, client: httpx.Client, timeout: float) -> tuple[ToolHealthStatus, float | None, str | None]:
    start = time.perf_counter()
    try:
        resp = client.get(url, timeout=timeout)
        latency = (time.perf_counter() - start) * 1000
        success = 200 <= resp.status_code < 300
        status = ToolHealthStatus.up if success else ToolHealthStatus.down
        error_detail = None if success else f"status={resp.status_code}"
        return status, latency, error_detail
    except httpx.RequestError as exc:
        latency = (time.perf_counter() - start) * 1000
        return ToolHealthStatus.down, latency, str(exc)


def refresh_all_tool_health(db: Session, timeout: float = 3.0) -> list[ToolHealth]:
    tools = db.scalars(select(Tool)).all()
    if not tools:
        return []

    results: list[ToolHealth] = []
    with httpx.Client(follow_redirects=True) as client:
        for tool in tools:
            if not tool.url:
                health = _create_or_refresh_health(
                    db,
                    tool.id,
                    ToolHealthStatus.unknown,
                    None,
                    "No URL configured",
                )
                results.append(health)
                continue
            status, latency, error = _check_tool_url(tool.url, client, timeout)
            health = _create_or_refresh_health(db, tool.id, status, latency, error)
            results.append(health)

    return results


def create_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before: dict | None = None,
    after: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    ctx = {"ip": None, "user_agent": None}
    if request:
        client = request.client
        ctx["ip"] = client.host if client else None
        ctx["user_agent"] = request.headers.get("user-agent")
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action.upper(),
        entity_type=entity_type.upper(),
        entity_id=entity_id,
        before=before,
        after=after,
        ip=ctx["ip"],
        user_agent=ctx["user_agent"],
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: int | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type.upper())
    if action:
        stmt = stmt.where(AuditLog.action == action.upper())
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if start:
        stmt = stmt.where(AuditLog.created_at >= start)
    if end:
        stmt = stmt.where(AuditLog.created_at <= end)

    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: int | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> int:
    stmt = select(func.count(AuditLog.id))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type.upper())
    if action:
        stmt = stmt.where(AuditLog.action == action.upper())
    if actor_user_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if start:
        stmt = stmt.where(AuditLog.created_at >= start)
    if end:
        stmt = stmt.where(AuditLog.created_at <= end)
    return int(db.scalar(stmt) or 0)
