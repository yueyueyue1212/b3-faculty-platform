from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    PromotionBatch,
    PromotionMaterial,
    PromotionRequirement,
    Teacher,
    User,
)
from ..schemas import BatchCreate, BatchUpdate, MaterialUpdate, RequirementCreate, RequirementUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import material_dict, requirement_dict, teacher_dict
from ..services.audit import write_audit
from ..services.promotion import (
    CATEGORY_LABELS,
    STATUS_LABELS,
    build_promotion_workbook,
    gather_materials,
    promotion_summary,
)

router = APIRouter(prefix="/api/promotion", tags=["职称申报"])

ALLOWED_STATUSES = set(STATUS_LABELS)
ALLOWED_CATEGORIES = set(CATEGORY_LABELS)


class GatherRequest(BaseModel):
    teacher_id: int | None = None
    teacher_ids: list[int] | None = None


def _batch_dict(batch: PromotionBatch, requirement_count: int = 0, material_count: int = 0) -> dict:
    return {
        "id": batch.id,
        "name": batch.name,
        "year": batch.year,
        "title_type": batch.title_type,
        "college": batch.college,
        "deadline": batch.deadline.isoformat() if batch.deadline else None,
        "status": batch.status,
        "requirement_count": requirement_count,
        "material_count": material_count,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


@router.get("/batches", summary="职称申报批次列表")
def list_batches(
    status: str | None = None,
    year: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PromotionBatch)
    if status:
        query = query.filter(PromotionBatch.status == status)
    if year:
        query = query.filter(PromotionBatch.year == year)
    batches = query.order_by(PromotionBatch.year.desc(), PromotionBatch.id.desc()).all()
    items = []
    for batch in batches:
        req_count = db.query(PromotionRequirement).filter(
            PromotionRequirement.batch_id == batch.id
        ).count()
        mat_count = db.query(PromotionMaterial).filter(
            PromotionMaterial.batch_id == batch.id
        ).count()
        items.append(_batch_dict(batch, req_count, mat_count))
    return {
        "items": items,
        "categories": [{"value": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        "material_statuses": [{"value": k, "label": v} for k, v in STATUS_LABELS.items()],
        "disclaimer": "申报条件由管理员配置，示例批次不代表任何高校的真实职称政策。",
    }


@router.post("/batches", summary="新增申报批次")
def create_batch(payload: BatchCreate, request: Request,
                 user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if payload.status not in ("draft", "open", "completed"):
        raise HTTPException(status_code=400, detail="批次状态不合法")
    batch = PromotionBatch(**payload.model_dump())
    db.add(batch)
    db.commit()
    db.refresh(batch)
    write_audit(db, user, "create", "promotion_batch", batch.id,
                f"新增职称申报批次 {batch.name}", client_ip(request))
    return _batch_dict(batch)


@router.put("/batches/{batch_id}", summary="修改申报批次")
def update_batch(batch_id: int, payload: BatchUpdate, request: Request,
                 user: User = Depends(require_editor), db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="申报批次不存在")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ("draft", "open", "completed"):
        raise HTTPException(status_code=400, detail="批次状态不合法")
    for key, value in data.items():
        setattr(batch, key, value)
    db.commit()
    db.refresh(batch)
    write_audit(db, user, "update", "promotion_batch", batch.id,
                f"修改申报批次 {batch.name}", client_ip(request))
    return _batch_dict(batch)


@router.delete("/batches/{batch_id}", summary="删除申报批次")
def delete_batch(batch_id: int, request: Request,
                 user: User = Depends(require_editor), db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="申报批次不存在")
    name = batch.name
    db.delete(batch)
    db.commit()
    write_audit(db, user, "delete", "promotion_batch", batch_id,
                f"删除申报批次 {name}", client_ip(request))
    return {"message": "批次已删除"}


@router.get("/batches/{batch_id}", summary="批次详情（含申报要求）")
def get_batch(batch_id: int, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="申报批次不存在")
    requirements = db.query(PromotionRequirement).filter(
        PromotionRequirement.batch_id == batch_id
    ).order_by(PromotionRequirement.id).all()
    data = _batch_dict(batch, len(requirements))
    data["requirements"] = [requirement_dict(r) for r in requirements]
    data["disclaimer"] = "申报要求为可配置示例，不代表真实高校政策；材料检查不验证成果真伪。"
    return data


@router.post("/batches/{batch_id}/requirements", summary="新增申报要求")
def create_requirement(batch_id: int, payload: RequirementCreate, request: Request,
                       user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if not db.get(PromotionBatch, batch_id):
        raise HTTPException(status_code=404, detail="申报批次不存在")
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="申报要求类别不合法")
    row = PromotionRequirement(batch_id=batch_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "promotion_requirement", row.id,
                f"新增申报要求 {row.name}", client_ip(request))
    return requirement_dict(row)


@router.put("/requirements/{requirement_id}", summary="修改申报要求")
def update_requirement(requirement_id: int, payload: RequirementUpdate, request: Request,
                       user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(PromotionRequirement, requirement_id)
    if not row:
        raise HTTPException(status_code=404, detail="申报要求不存在")
    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"] not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="申报要求类别不合法")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "promotion_requirement", row.id,
                f"修改申报要求 {row.name}", client_ip(request))
    return requirement_dict(row)


@router.delete("/requirements/{requirement_id}", summary="删除申报要求")
def delete_requirement(requirement_id: int, request: Request,
                       user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(PromotionRequirement, requirement_id)
    if not row:
        raise HTTPException(status_code=404, detail="申报要求不存在")
    db.query(PromotionMaterial).filter(
        PromotionMaterial.requirement_id == requirement_id
    ).delete()
    name = row.name
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "promotion_requirement", requirement_id,
                f"删除申报要求 {name}", client_ip(request))
    return {"message": "申报要求已删除"}


@router.get("/batches/{batch_id}/teachers", summary="批次范围内的教师及材料进度")
def batch_teachers(
    batch_id: int,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.get(PromotionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="申报批次不存在")
    query = db.query(Teacher)
    if batch.college:
        query = query.filter(Teacher.college == batch.college)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(Teacher.name.like(pattern), Teacher.teacher_no.like(pattern)))
    total = query.count()
    teachers = (query.order_by(Teacher.teacher_no)
                .offset((page - 1) * page_size).limit(page_size).all())
    ids = [t.id for t in teachers]
    stats = {}
    if ids:
        rows = (db.query(PromotionMaterial.teacher_id, PromotionMaterial.status,
                         func.count(PromotionMaterial.id))
                .filter(PromotionMaterial.batch_id == batch_id,
                        PromotionMaterial.teacher_id.in_(ids))
                .group_by(PromotionMaterial.teacher_id, PromotionMaterial.status).all())
        for teacher_id, status, count in rows:
            stats.setdefault(teacher_id, {})[status] = count
    items = []
    for teacher in teachers:
        item = teacher_dict(teacher, user)
        item["material_stats"] = stats.get(teacher.id, {})
        item["material_total"] = sum(stats.get(teacher.id, {}).values())
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.post("/batches/{batch_id}/gather", summary="自动归集申报材料")
def gather(batch_id: int, payload: GatherRequest, request: Request,
           user: User = Depends(require_editor), db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="申报批次不存在")
    ids = []
    if payload.teacher_id:
        ids.append(payload.teacher_id)
    if payload.teacher_ids:
        ids.extend(payload.teacher_ids)
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要归集的教师")
    results = []
    for teacher_id in ids:
        teacher = db.get(Teacher, teacher_id)
        if not teacher:
            results.append({"teacher_id": teacher_id, "error": "教师不存在"})
            continue
        result = gather_materials(db, batch, teacher)
        summary = promotion_summary(db, batch, teacher_id)
        results.append({
            "teacher_id": teacher_id,
            "teacher_name": teacher.name,
            "created": result["created"],
            "completion": summary["completion"],
            "missing_mandatory": len(summary["missing_mandatory"]),
        })
    write_audit(db, user, "gather", "promotion_batch", batch_id,
                f"归集材料：教师 {ids}，批次 {batch.name}", client_ip(request))
    return {"batch_id": batch_id, "results": results}


@router.get("/materials", summary="申报材料列表")
def list_materials(
    batch_id: int = Query(...),
    teacher_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PromotionMaterial).filter(PromotionMaterial.batch_id == batch_id)
    if teacher_id:
        query = query.filter(PromotionMaterial.teacher_id == teacher_id)
    if status:
        query = query.filter(PromotionMaterial.status == status)
    if category:
        query = query.filter(PromotionMaterial.category == category)
    total = query.count()
    rows = (query.order_by(PromotionMaterial.requirement_id, PromotionMaterial.id)
            .offset((page - 1) * page_size).limit(page_size).all())
    requirement_names = {
        r.id: r.name for r in db.query(PromotionRequirement)
        .filter(PromotionRequirement.batch_id == batch_id).all()
    }
    items = []
    for row in rows:
        item = material_dict(row)
        item["requirement_name"] = requirement_names.get(row.requirement_id)
        item["status_label"] = STATUS_LABELS.get(row.status, row.status)
        item["category_label"] = CATEGORY_LABELS.get(row.category, row.category)
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.put("/materials/{material_id}", summary="人工确认/驳回/备注材料")
def update_material(material_id: int, payload: MaterialUpdate, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(PromotionMaterial, material_id)
    if not row:
        raise HTTPException(status_code=404, detail="材料记录不存在")
    if payload.status and payload.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="材料状态不合法")
    if payload.status:
        row.status = payload.status
    if payload.note is not None:
        row.note = payload.note
    row.updated_by = user.username
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "promotion_material", row.id,
                f"材料《{row.title}》状态改为 {row.status}；备注：{row.note or ''}",
                client_ip(request))
    return material_dict(row)


@router.get("/batches/{batch_id}/summary", summary="教师申报汇总检查")
def batch_summary(batch_id: int, teacher_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    teacher = db.get(Teacher, teacher_id)
    if not batch or not teacher:
        raise HTTPException(status_code=404, detail="批次或教师不存在")
    summary = promotion_summary(db, batch, teacher_id)
    summary["teacher"] = teacher_dict(teacher, user)
    summary["categories"] = CATEGORY_LABELS
    return summary


@router.get("/batches/{batch_id}/export", summary="导出申报材料汇总（Excel）")
def export_batch(batch_id: int, teacher_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    batch = db.get(PromotionBatch, batch_id)
    teacher = db.get(Teacher, teacher_id)
    if not batch or not teacher:
        raise HTTPException(status_code=404, detail="批次或教师不存在")
    summary = promotion_summary(db, batch, teacher_id)
    stream = build_promotion_workbook(summary, teacher)
    filename = f"promotion_{batch_id}_{teacher.teacher_no}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}; "
            f"filename*=UTF-8''{quote('职称申报材料汇总.xlsx')}"
        },
    )
