from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import ResearchOutput, Teacher, User
from ..schemas import ResearchOutputCreate, ResearchOutputUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import output_dict
from ..services.audit import write_audit

router = APIRouter(prefix="/api/research-outputs", tags=["科研成果"])


@router.get("", summary="科研成果列表")
def list_outputs(
    teacher_id: int | None = None,
    college: str | None = None,
    discipline: str | None = None,
    output_type: str | None = None,
    level: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchOutput).join(Teacher, ResearchOutput.teacher_id == Teacher.id)
    if teacher_id:
        query = query.filter(ResearchOutput.teacher_id == teacher_id)
    if college:
        query = query.filter(Teacher.college == college)
    if discipline:
        query = query.filter(Teacher.discipline == discipline)
    if output_type:
        query = query.filter(ResearchOutput.output_type == output_type)
    if level:
        query = query.filter(ResearchOutput.level == level)
    if year_from:
        query = query.filter(ResearchOutput.publish_date >= __import__("datetime").date(year_from, 1, 1))
    if year_to:
        query = query.filter(ResearchOutput.publish_date <= __import__("datetime").date(year_to, 12, 31))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            ResearchOutput.title.like(pattern),
            ResearchOutput.venue.like(pattern),
            ResearchOutput.authors.like(pattern),
            Teacher.name.like(pattern),
            Teacher.teacher_no.like(pattern),
        ))
    total = query.count()
    rows = (
        query.options(joinedload(ResearchOutput.teacher))
        .order_by(ResearchOutput.publish_date.desc(), ResearchOutput.id.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    items = []
    for row in rows:
        item = output_dict(row)
        item["teacher_name"] = row.teacher.name if row.teacher else None
        item["teacher_no"] = row.teacher.teacher_no if row.teacher else None
        item["college"] = row.teacher.college if row.teacher else None
        item["discipline"] = row.teacher.discipline if row.teacher else None
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.post("", summary="新增科研成果")
def create_output(payload: ResearchOutputCreate, request: Request,
                  user: User = Depends(require_editor), db: Session = Depends(get_db)):
    teacher = db.get(Teacher, payload.teacher_id)
    if not teacher:
        raise HTTPException(status_code=400, detail="关联教师不存在")
    row = ResearchOutput(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "research_output", row.id,
                f"新增成果《{row.title}》教师 {teacher.teacher_no}", client_ip(request))
    return output_dict(row)


@router.put("/{output_id}", summary="修改科研成果")
def update_output(output_id: int, payload: ResearchOutputUpdate, request: Request,
                  user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ResearchOutput, output_id)
    if not row:
        raise HTTPException(status_code=404, detail="成果记录不存在")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "research_output", row.id,
                f"修改成果《{row.title}》", client_ip(request))
    return output_dict(row)


@router.delete("/{output_id}", summary="删除科研成果")
def delete_output(output_id: int, request: Request,
                  user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ResearchOutput, output_id)
    if not row:
        raise HTTPException(status_code=404, detail="成果记录不存在")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "research_output", output_id,
                f"删除成果《{row.title}》", client_ip(request))
    return {"message": "成果已删除"}
