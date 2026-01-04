from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..crud import count_user_favorites, list_user_favorites
from ..deps import get_current_user, get_db
from ..models import Tool, User
from ..schemas import ToolListResponse, ToolOut

router = APIRouter(prefix="/api/me", tags=["me"])


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


@router.get("/favorites", response_model=ToolListResponse)
def favorites(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ToolListResponse:
    offset = (page - 1) * page_size
    total = count_user_favorites(db, user.id)
    tools = list_user_favorites(db, user.id, limit=page_size, offset=offset)
    pages = math.ceil(total / page_size) if total else 0
    return ToolListResponse(
        items=[_build_tool_out(tool) for tool in tools],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
