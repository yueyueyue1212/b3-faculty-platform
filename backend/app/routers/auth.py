from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import LoginRequest
from ..security import (
    client_ip,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..serializers import user_dict
from ..services.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["认证"])


class ChangePassword(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=100)


@router.post("/login", summary="用户登录")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit(
            db, None, "login_failed", "auth",
            detail=f"用户名：{payload.username}", ip=client_ip(request),
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")
    token = create_access_token(user)
    write_audit(db, user, "login", "auth", detail="登录成功", ip=client_ip(request))
    return {"access_token": token, "token_type": "bearer", "user": user_dict(user)}


@router.get("/me", summary="当前用户信息")
def me(user: User = Depends(get_current_user)):
    return user_dict(user)


@router.post("/change-password", summary="修改自己的密码")
def change_password(payload: ChangePassword, request: Request,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    write_audit(db, user, "change_password", "user", user.id, "修改本人密码", client_ip(request))
    return {"message": "密码已修改"}
