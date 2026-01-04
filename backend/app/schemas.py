from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=200)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=200)
    role: str | None = Field(default=None, pattern="^(admin|user)$")


class ToolOut(BaseModel):
    id: int
    name: str
    description: str
    url: str
    category: str
    tags: list[str]
    created_at: datetime


class ToolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    url: str = ""
    category: str = Field(default="general", min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_items=20)


class ToolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    url: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    tags: list[str] | None = Field(default=None, max_items=20)


class ToolListResponse(BaseModel):
    items: list[ToolOut]
    total: int
    page: int
    page_size: int
    pages: int


class ToolHealthOut(BaseModel):
    tool_id: int
    status: str
    last_checked_at: datetime | None
    latency_ms: float | None
    last_error: str | None


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    before: dict | None
    after: dict | None
    created_at: datetime
    ip: str | None
    user_agent: str | None


class AuditListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
    pages: int
