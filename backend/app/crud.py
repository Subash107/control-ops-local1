from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from .models import User, Tool
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
    return list(db.scalars(select(User).order_by(User.id)).all())


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def _apply_tool_filters(stmt, *, category: str | None, tag: str | None, q: str | None):
    if category:
        stmt = stmt.where(func.lower(Tool.category) == category.lower())

    if tag:
        stmt = stmt.where(Tool.tags.contains([tag]))

    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Tool.name).like(like),
                func.lower(Tool.description).like(like),
                func.lower(Tool.category).like(like),
            )
        )
    return stmt


def _tool_sort_column(sort_by: str):
    sort_by = (sort_by or "created_at").lower()
    return {
        "name": Tool.name,
        "category": Tool.category,
        "created_at": Tool.created_at,
    }.get(sort_by, Tool.created_at)


def list_tools(
    db: Session,
    *,
    category: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    sort_spec: list[tuple[str, str]] | None = None,
) -> list[Tool]:
    # sort_spec: list of (field, dir). If provided, takes precedence over sort_by/sort_dir.
    order_by = []

    if sort_spec:
        for field, direction in sort_spec:
            col = _tool_sort_column(field)
            order_by.append(col.asc() if (direction or "asc").lower() == "asc" else col.desc())
    else:
        col = _tool_sort_column(sort_by)
        order_by.append(col.asc() if (sort_dir or "desc").lower() == "asc" else col.desc())

    # Deterministic tiebreaker.
    order_by.append(Tool.id.desc())

    stmt = select(Tool).order_by(*order_by).limit(limit).offset(offset)
    stmt = _apply_tool_filters(stmt, category=category, tag=tag, q=q)

    return list(db.scalars(stmt).all())


def count_tools(
    db: Session,
    *,
    category: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> int:
    stmt = select(func.count(Tool.id))
    stmt = _apply_tool_filters(stmt, category=category, tag=tag, q=q)
    return int(db.scalar(stmt) or 0)


def list_tool_categories(db: Session) -> list[str]:
    stmt = select(Tool.category).distinct().order_by(Tool.category)
    return [r[0] for r in db.execute(stmt).all() if r[0]]


def list_tool_tags(db: Session) -> list[str]:
    tag = func.jsonb_array_elements_text(Tool.tags).label("tag")
    stmt = select(tag).distinct().order_by(tag)
    return [r[0] for r in db.execute(stmt).all() if r[0]]


class DuplicateNameError(Exception):
    pass


def create_tool(db: Session, name: str, description: str, url: str, category: str, tags: list[str]) -> Tool:
    tool = Tool(name=name, description=description, url=url, category=category, tags=tags)
    db.add(tool)
    try:
        db.commit()
    except Exception as e:
        # detect unique constraint on name via DB driver message and translate
        if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower() or 'ix_tools_name' in str(e):
            db.rollback()
            raise DuplicateNameError('Tool name already exists') from e
        db.rollback()
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
        tool.name = name
    if description is not None:
        tool.description = description
    if url is not None:
        tool.url = url
    if category is not None:
        tool.category = category
    if tags is not None:
        tool.tags = tags

    db.add(tool)
    try:
        db.commit()
    except Exception as e:
        if 'unique constraint' in str(e).lower() or 'duplicate key' in str(e).lower() or 'ix_tools_name' in str(e):
            db.rollback()
            raise DuplicateNameError('Tool name already exists') from e
        db.rollback()
        raise
    db.refresh(tool)
    return tool


def delete_tool(db: Session, tool: Tool) -> None:
    db.delete(tool)
    db.commit()
