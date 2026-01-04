from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user, require_admin
from ..models import Tool, User
from ..schemas import ToolOut, ToolCreate, ToolUpdate, ToolListResponse
from ..crud import (
    list_tools,
    count_tools,
    create_tool,
    update_tool,
    delete_tool,
    list_tool_categories,
    list_tool_tags,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])

_ALLOWED_SORT_FIELDS = {"name", "category", "created_at"}
_ALLOWED_SORT_DIRS = {"asc", "desc"}


def _parse_sort(sort: str | None) -> list[tuple[str, str]] | None:
    """Parse sort like: 'category:asc,name:asc' or 'created_at:desc'.

    Strict validation:
    - unknown fields -> 422
    - invalid dir -> 422
    - duplicates -> 422
    - more than 3 fields -> 422
    """
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

    for p in parts:
        if ":" in p:
            field, direction = [x.strip().lower() for x in p.split(":", 1)]
        else:
            field, direction = p.strip().lower(), "asc"

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


@router.get("", response_model=ToolListResponse)
def get_tools(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search in name/description/category"),
    limit: int = Query(default=20, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    # Backwards compatible (single-column):
    sort_by: str = Query(default="created_at", pattern="^(name|category|created_at)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    # Multi-column:
    sort: str | None = Query(default=None, description="e.g. category:asc,name:asc"),
) -> ToolListResponse:
    sort_spec = _parse_sort(sort)

    tools = list_tools(
        db,
        category=category,
        tag=tag,
        q=q,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_spec=sort_spec,
    )
    total = count_tools(db, category=category, tag=tag, q=q)

    items = [
        ToolOut(
            id=t.id,
            name=t.name,
            description=t.description,
            url=t.url,
            category=t.category,
            tags=t.tags or [],
            created_at=t.created_at,
        )
        for t in tools
    ]

    return ToolListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/categories", response_model=list[str])
def categories(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[str]:
    return list_tool_categories(db)


@router.get("/tags", response_model=list[str])
def tags(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[str]:
    return list_tool_tags(db)


from sqlalchemy.exc import IntegrityError
from ..crud import DuplicateNameError


@router.post("", response_model=ToolOut)
def create(payload: ToolCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> ToolOut:
    try:
        tool = create_tool(db, payload.name, payload.description, payload.url, payload.category, payload.tags)
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
    except IntegrityError as e:
        # Fallback: if a DB integrity error appears and wasn't caught above
        if 'ix_tools_name' in str(e.orig) or 'unique constraint' in str(e.orig).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
        raise

    return ToolOut(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        url=tool.url,
        category=tool.category,
        tags=tool.tags or [],
        created_at=tool.created_at,
    )


@router.put("/{tool_id}", response_model=ToolOut)
def update(
    tool_id: int,
    payload: ToolUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ToolOut:
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    try:
        tool = update_tool(db, tool, payload.name, payload.description, payload.url, payload.category, payload.tags)
    except DuplicateNameError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
    except IntegrityError as e:
        if 'ix_tools_name' in str(e.orig) or 'unique constraint' in str(e.orig).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'field': 'name', 'message': 'Tool name already exists'})
        raise
    return ToolOut(
        id=tool.id,
        name=tool.name,
        description=tool.description,
        url=tool.url,
        category=tool.category,
        tags=tool.tags or [],
        created_at=tool.created_at,
    )


@router.delete("/{tool_id}")
def remove(tool_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    delete_tool(db, tool)
    return {"ok": True}
