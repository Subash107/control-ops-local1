from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..crud import (
    add_favorite,
    count_tools,
    create_audit_log,
    create_tool,
    delete_tool,
    DuplicateNameError,
    get_tool_by_id,
    get_tool_health,
    list_tool_categories,
    list_tool_tags,
    list_tools,
    remove_favorite,
    tool_to_dict,
    update_tool,
)
from ..deps import get_current_user, get_db, require_admin
from ..models import Tool, ToolHealthStatus, User
from ..schemas import ToolCreate, ToolHealthOut, ToolListResponse, ToolOut, ToolUpdate

router = APIRouter(prefix="/api/tools", tags=["tools"])

_ALLOWED_SORT_FIELDS = {"name", "category", "created_at"}
_ALLOWED_SORT_DIRS = {"asc", "desc"}


def _parse_sort(sort: str | None) -> list[tuple[str, str]] | None:
    if not sort:
        return None

    parts = [p.strip() for p in sort.split(",") if p.strip()]
    if not parts:
        return None

    if len(parts) > 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort supports at most 3 fields",
        )

    spec: list[tuple[str, str]] = []
    seen: set[str] = set()

    for part in parts:
        if ":" in part:
            field, direction = [x.strip().lower() for x in part.split(":", 1)]
        else:
            field, direction = part.strip().lower(), "asc"

        if field not in _ALLOWED_SORT_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort field '{field}'. Allowed: {sorted(_ALLOWED_SORT_FIELDS)}",
            )

        if field in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate sort field '{field}'",
            )
        seen.add(field)

        if direction not in _ALLOWED_SORT_DIRS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort direction '{direction}'. Allowed: {sorted(_ALLOWED_SORT_DIRS)}",
            )

        spec.append((field, direction))

    return spec or None


def _build_tool_out(tool: Tool) -> ToolOut:
    return ToolOut(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        url=tool.url,
        category=tool.category,
        tags=[tag.name for tag in tool.tags or []],
        created_at=tool.created_at,
    )


@router.get("", response_model=ToolListResponse)
def get_tools(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in name/description"),
    q: str | None = Query(default=None, description="Legacy search (alias for search)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int | None = Query(default=None, ge=0),
    sort_by: str = Query(default="created_at", pattern="^(name|category|created_at)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    sort: str | None = Query(default=None, description="e.g. category:asc,name:asc"),
) -> ToolListResponse:
    sort_spec = _parse_sort(sort)
    search_term = search or q

    effective_limit = limit if limit is not None else page_size
    effective_offset = offset if offset is not None else (page - 1) * page_size

    tools = list_tools(
        db,
        category=category,
        tag=tag,
        search=search_term,
        limit=effective_limit,
        offset=effective_offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_spec=sort_spec,
    )
    total = count_tools(db, category=category, tag=tag, search=search_term)
    pages = math.ceil(total / page_size) if total else 0

    items = [_build_tool_out(t) for t in tools]
    return ToolListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.get("/categories", response_model=list[str])
def categories(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[str]:
    return list_tool_categories(db)


@router.get("/tags", response_model=list[str])
def tags(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[str]:
    return list_tool_tags(db)


@router.get("/{tool_id}", response_model=ToolOut)
def get_tool(tool_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ToolOut:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return _build_tool_out(tool)


@router.post("", response_model=ToolOut)
def create(
    payload: ToolCreate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ToolOut:
    try:
        tool = create_tool(db, payload.name, payload.description, payload.url, payload.category, payload.tags)
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
    except IntegrityError as exc:
        if 'ix_tools_name' in str(exc.orig) or 'unique constraint' in str(exc.orig).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="CREATE",
        entity_type="TOOL",
        entity_id=tool.id,
        after=tool_to_dict(tool),
        request=request,
    )
    return _build_tool_out(tool)


@router.put("/{tool_id}", response_model=ToolOut)
def update(
    tool_id: int,
    payload: ToolUpdate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ToolOut:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    before = tool_to_dict(tool)
    try:
        tool = update_tool(db, tool, payload.name, payload.description, payload.url, payload.category, payload.tags)
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
    except IntegrityError as exc:
        if 'ix_tools_name' in str(exc.orig) or 'unique constraint' in str(exc.orig).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="UPDATE",
        entity_type="TOOL",
        entity_id=tool.id,
        before=before,
        after=tool_to_dict(tool),
        request=request,
    )
    return _build_tool_out(tool)


@router.delete("/{tool_id}")
def remove(
    tool_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    before = tool_to_dict(tool)
    delete_tool(db, tool)
    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="DELETE",
        entity_type="TOOL",
        entity_id=tool_id,
        before=before,
        request=request,
    )
    return {"ok": True}


@router.post("/{tool_id}/favorite")
def favorite(tool_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    add_favorite(db, user.id, tool_id)
    return {"ok": True}


@router.delete("/{tool_id}/favorite")
def unfavorite(tool_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    remove_favorite(db, user.id, tool_id)
    return {"ok": True}


@router.get("/{tool_id}/health", response_model=ToolHealthOut)
def tool_health_endpoint(tool_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ToolHealthOut:
    tool = get_tool_by_id(db, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    health = get_tool_health(db, tool_id)
    if not health:
        return ToolHealthOut(
            tool_id=tool_id,
            status=ToolHealthStatus.unknown.value,
            last_checked_at=None,
            latency_ms=None,
            last_error=None,
        )

    return ToolHealthOut(
        tool_id=tool_id,
        status=health.status.value,
        last_checked_at=health.last_checked_at,
        latency_ms=health.latency_ms,
        last_error=health.last_error,
    )
