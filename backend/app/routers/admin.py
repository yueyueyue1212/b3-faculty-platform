import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import (
    APP_VERSION,
    DATABASE_URL,
    DEFAULT_ADVISOR_WEIGHTS,
    DEFAULT_CANDIDATE_WEIGHTS,
)
from ..database import get_db
from ..models import (
    AuditLog,
    CandidateProfile,
    JobPosition,
    PromotionBatch,
    ResearchOutput,
    ResearchProject,
    StudentProfile,
    SystemSetting,
    Teacher,
    User,
)
from ..schemas import UserCreate, UserUpdate
from ..security import (
    client_ip,
    get_current_user,
    hash_password,
    require_admin,
    require_editor,
)
from ..serializers import user_dict
from ..services.audit import write_audit
from ..services.llm import llm_public_status
from ..services.matching import normalize_weights

router = APIRouter(prefix="/api", tags=["系统管理"])


class TalentPlanItem(BaseModel):
    college: str = Field(min_length=1, max_length=80)
    discipline: str = Field(min_length=1, max_length=80)
    target_count: int = Field(ge=0, le=10000)
    note: str = ""


class TalentPlanPayload(BaseModel):
    items: list[TalentPlanItem]


class WeightsPayload(BaseModel):
    advisor_weights: dict[str, float] | None = None
    candidate_weights: dict[str, float] | None = None


def _get_setting(db: Session, key: str, default: dict) -> dict:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        return default
    try:
        return json.loads(row.value)
    except json.JSONDecodeError:
        return default


def _set_setting(db: Session, key: str, value, description: str, admin: User, request: Request):
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    serialized = json.dumps(value, ensure_ascii=False)
    if row:
        row.value = serialized
        row.description = description
    else:
        row = SystemSetting(key=key, value=serialized, description=description)
        db.add(row)
    db.commit()
    write_audit(db, admin, "update_setting", "system_setting", key,
                description, client_ip(request))


@router.get("/users", summary="用户列表（管理员）")
def list_users(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.id).all()
    return {"items": [user_dict(u) for u in rows], "total": len(rows)}


@router.post("/users", summary="新增用户（管理员）")
def create_user(payload: UserCreate, request: Request,
                admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    row = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        role=payload.role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, admin, "create", "user", row.id,
                f"新增用户 {row.username}（{row.role}）", client_ip(request))
    return user_dict(row)


@router.put("/users/{user_id}", summary="修改用户（管理员）")
def update_user(user_id: int, payload: UserUpdate, request: Request,
                admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = payload.model_dump(exclude_unset=True)
    if row.id == admin.id and data.get("is_active") is False:
        raise HTTPException(status_code=400, detail="不能停用当前登录账号")
    if row.id == admin.id and data.get("role") and data["role"] != "admin":
        raise HTTPException(status_code=400, detail="不能修改当前登录账号的管理员角色")
    if "password" in data and data["password"]:
        row.password_hash = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, admin, "update", "user", row.id,
                f"修改用户 {row.username}，字段：{', '.join(payload.model_fields_set)}",
                client_ip(request))
    return user_dict(row)


@router.get("/audit-logs", summary="操作审计日志")
def list_audit_logs(
    username: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if username:
        query = query.filter(AuditLog.username.like(f"%{username}%"))
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))
    total = query.count()
    rows = (query.order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "items": [
            {
                "id": r.id,
                "username": r.username,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "detail": r.detail,
                "ip": r.ip,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/settings", summary="系统设置与权重")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    talent_plan = db.query(SystemSetting).filter(SystemSetting.key == "talent_plan").first()
    plan_items = []
    if talent_plan:
        try:
            plan_items = json.loads(talent_plan.value)
        except json.JSONDecodeError:
            plan_items = []
    return {
        "advisor_weights": _get_setting(db, "advisor_weights", DEFAULT_ADVISOR_WEIGHTS),
        "candidate_weights": _get_setting(db, "candidate_weights", DEFAULT_CANDIDATE_WEIGHTS),
        "talent_plan": plan_items,
        "llm": llm_public_status(),
        "role": user.role,
        "can_edit": user.role == "admin",
    }


@router.put("/settings/weights", summary="修改默认评分权重（管理员）")
def update_weights(payload: WeightsPayload, request: Request,
                   admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        if payload.advisor_weights is not None:
            advisor = normalize_weights(
                payload.advisor_weights, DEFAULT_ADVISOR_WEIGHTS, set(DEFAULT_ADVISOR_WEIGHTS)
            )
            _set_setting(db, "advisor_weights", advisor, "默认导师匹配权重", admin, request)
        if payload.candidate_weights is not None:
            candidate = normalize_weights(
                payload.candidate_weights, DEFAULT_CANDIDATE_WEIGHTS, set(DEFAULT_CANDIDATE_WEIGHTS)
            )
            _set_setting(db, "candidate_weights", candidate, "默认人才引进评分权重", admin, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return get_settings(admin, db)


@router.put("/settings/talent-plan", summary="配置人才规划目标（管理员）")
def update_talent_plan(payload: TalentPlanPayload, request: Request,
                       admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = [item.model_dump() for item in payload.items]
    _set_setting(db, "talent_plan", items, "管理员配置的人才规划目标", admin, request)
    return {"items": items, "message": "人才规划已保存"}


@router.get("/system/info", summary="系统信息与运行状态")
def system_info(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    database = DATABASE_URL.split("://", 1)[0]
    if "sqlite" in database:
        database_name = DATABASE_URL.rsplit("/", 1)[-1]
    else:
        database_name = "外部数据库（连接串已隐藏）"
    return {
        "app": "高校师资/人才智能画像与辅助管理平台",
        "project_no": "B3",
        "version": APP_VERSION,
        "database": {
            "backend": database,
            "name": database_name,
            "note": "通过 SQLAlchemy 访问，可迁移至 MySQL/PostgreSQL",
        },
        "counts": {
            "teachers": db.query(Teacher).count(),
            "research_outputs": db.query(ResearchOutput).count(),
            "research_projects": db.query(ResearchProject).count(),
            "students": db.query(StudentProfile).count(),
            "promotion_batches": db.query(PromotionBatch).count(),
            "job_positions": db.query(JobPosition).count(),
            "candidates": db.query(CandidateProfile).count(),
        },
        "llm": llm_public_status(),
        "demo_data": {
            "enabled": db.query(Teacher).filter(Teacher.data_source.like("%模拟数据%")).count() > 0,
            "marker": "模拟数据（B3演示）",
            "note": "演示数据仅用于功能展示，不代表真实高校数据或个人评价。",
        },
        "role": user.role,
    }
