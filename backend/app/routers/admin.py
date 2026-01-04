from __future__ import annotations

import datetime
import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..crud import (
    count_audit_logs,
    create_audit_log,
    create_user,
    delete_user,
    get_user_by_username,
    list_audit_logs,
    list_users,
    refresh_all_tool_health,
    update_user,
)
from ..deps import get_db, require_admin
from ..models import User
from ..schemas import AuditListResponse, AuditLogOut, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _serialize_user(user: User) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role}


@router.get("/users", response_model=list[UserOut])
def users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserOut]:
    return [UserOut(id=u.id, username=u.username, role=u.role) for u in list_users(db)]


@router.post("/users", response_model=UserOut)
def create(payload: UserCreate, request: Request, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    if get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = create_user(db, payload.username, payload.password, payload.role)
    create_audit_log(
        db,
        actor_user_id=_.id,
        action="CREATE",
        entity_type="USER",
        entity_id=user.id,
        after=_serialize_user(user),
        request=request,
    )
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.put("/users/{user_id}", response_model=UserOut)
def update(user_id: int, payload: UserUpdate, request: Request, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before = _serialize_user(user)
    user = update_user(db, user, payload.password, payload.role)
    create_audit_log(
        db,
        actor_user_id=_.id,
        action="UPDATE",
        entity_type="USER",
        entity_id=user.id,
        before=before,
        after=_serialize_user(user),
        request=request,
    )
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.delete("/users/{user_id}")
def delete(user_id: int, request: Request, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before = _serialize_user(user)
    delete_user(db, user)
    create_audit_log(
        db,
        actor_user_id=_.id,
        action="DELETE",
        entity_type="USER",
        entity_id=user_id,
        before=before,
        request=request,
    )
    return {"ok": True}


@router.get("/audit", response_model=AuditListResponse)
def audit_logs(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    start: datetime.datetime | None = Query(default=None, alias="from"),
    end: datetime.datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditListResponse:
    total = count_audit_logs(
        db,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        start=start,
        end=end,
    )
    logs = list_audit_logs(
        db,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        start=start,
        end=end,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    items = [
        AuditLogOut(
            id=log.id,
            actor_user_id=log.actor_user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before=log.before,
            after=log.after,
            created_at=log.created_at,
            ip=log.ip,
            user_agent=log.user_agent,
        )
        for log in logs
    ]
    pages = math.ceil(total / page_size) if total else 0
    return AuditListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("/tools/health/refresh")
def refresh_tool_health(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = refresh_all_tool_health(db)
    return {"checked": len(items)}
