from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, require_admin
from ..models import User
from ..schemas import UserOut, UserCreate, UserUpdate
from ..crud import list_users, create_user, update_user, delete_user, get_user_by_username

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[UserOut]:
    return [UserOut(id=u.id, username=u.username, role=u.role) for u in list_users(db)]


@router.post("/users", response_model=UserOut)
def create(payload: UserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    if get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    u = create_user(db, payload.username, payload.password, payload.role)
    return UserOut(id=u.id, username=u.username, role=u.role)


@router.put("/users/{user_id}", response_model=UserOut)
def update(user_id: int, payload: UserUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    u = update_user(db, u, payload.password, payload.role)
    return UserOut(id=u.id, username=u.username, role=u.role)


@router.delete("/users/{user_id}")
def delete(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    delete_user(db, u)
    return {"ok": True}
