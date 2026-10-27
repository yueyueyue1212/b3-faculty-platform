from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import ServiceRecord, Teacher, TeachingRecord, User
from ..schemas import (
    ServiceCreate,
    ServiceUpdate,
    TeachingCreate,
    TeachingUpdate,
)
from ..security import client_ip, get_current_user, require_editor
from ..serializers import service_dict, teaching_dict
from ..services.audit import write_audit

teaching_router = APIRouter(prefix="/api/teaching-records", tags=["教学记录"])
service_router = APIRouter(prefix="/api/service-records", tags=["社会服务"])


@teaching_router.get("", summary="教学记录列表")
def list_teaching(
    teacher_id: int | None = None,
    college: str | None = None,
    discipline: str | None = None,
    academic_year: str | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(TeachingRecord).join(Teacher, TeachingRecord.teacher_id == Teacher.id)
    if teacher_id:
        query = query.filter(TeachingRecord.teacher_id == teacher_id)
    if college:
        query = query.filter(Teacher.college == college)
    if discipline:
        query = query.filter(Teacher.discipline == discipline)
    if academic_year:
        query = query.filter(TeachingRecord.academic_year == academic_year)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            TeachingRecord.course_name.like(pattern),
            TeachingRecord.achievement.like(pattern),
            Teacher.name.like(pattern),
        ))
    total = query.count()
    rows = (query.options(joinedload(TeachingRecord.teacher))
            .order_by(TeachingRecord.academic_year.desc(), TeachingRecord.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = []
    for row in rows:
        item = teaching_dict(row)
        item["teacher_name"] = row.teacher.name if row.teacher else None
        item["teacher_no"] = row.teacher.teacher_no if row.teacher else None
        item["college"] = row.teacher.college if row.teacher else None
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@teaching_router.post("", summary="新增教学记录")
def create_teaching(payload: TeachingCreate, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if not db.get(Teacher, payload.teacher_id):
        raise HTTPException(status_code=400, detail="关联教师不存在")
    row = TeachingRecord(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "teaching_record", row.id,
                f"新增教学记录 {row.course_name}", client_ip(request))
    return teaching_dict(row)


@teaching_router.put("/{record_id}", summary="修改教学记录")
def update_teaching(record_id: int, payload: TeachingUpdate, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(TeachingRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="教学记录不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "teaching_record", row.id,
                f"修改教学记录 {row.course_name}", client_ip(request))
    return teaching_dict(row)


@teaching_router.delete("/{record_id}", summary="删除教学记录")
def delete_teaching(record_id: int, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(TeachingRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="教学记录不存在")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "teaching_record", record_id,
                f"删除教学记录 {row.course_name}", client_ip(request))
    return {"message": "教学记录已删除"}


@service_router.get("", summary="社会服务/获奖/学术任职列表")
def list_services(
    teacher_id: int | None = None,
    college: str | None = None,
    discipline: str | None = None,
    service_type: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ServiceRecord).join(Teacher, ServiceRecord.teacher_id == Teacher.id)
    if teacher_id:
        query = query.filter(ServiceRecord.teacher_id == teacher_id)
    if college:
        query = query.filter(Teacher.college == college)
    if discipline:
        query = query.filter(Teacher.discipline == discipline)
    if service_type:
        query = query.filter(ServiceRecord.service_type == service_type)
    if year_from:
        query = query.filter(ServiceRecord.start_date >= date(year_from, 1, 1))
    if year_to:
        query = query.filter(ServiceRecord.start_date <= date(year_to, 12, 31))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            ServiceRecord.name.like(pattern),
            ServiceRecord.organization.like(pattern),
            Teacher.name.like(pattern),
        ))
    total = query.count()
    rows = (query.options(joinedload(ServiceRecord.teacher))
            .order_by(ServiceRecord.start_date.desc(), ServiceRecord.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = []
    for row in rows:
        item = service_dict(row)
        item["teacher_name"] = row.teacher.name if row.teacher else None
        item["teacher_no"] = row.teacher.teacher_no if row.teacher else None
        item["college"] = row.teacher.college if row.teacher else None
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@service_router.post("", summary="新增社会服务记录")
def create_service(payload: ServiceCreate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if not db.get(Teacher, payload.teacher_id):
        raise HTTPException(status_code=400, detail="关联教师不存在")
    row = ServiceRecord(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "service_record", row.id,
                f"新增社会服务 {row.name}", client_ip(request))
    return service_dict(row)


@service_router.put("/{record_id}", summary="修改社会服务记录")
def update_service(record_id: int, payload: ServiceUpdate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ServiceRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "service_record", row.id,
                f"修改社会服务 {row.name}", client_ip(request))
    return service_dict(row)


@service_router.delete("/{record_id}", summary="删除社会服务记录")
def delete_service(record_id: int, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ServiceRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "service_record", record_id,
                f"删除社会服务 {row.name}", client_ip(request))
    return {"message": "记录已删除"}
