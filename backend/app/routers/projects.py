from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import ProjectMember, ResearchProject, Teacher, User
from ..schemas import ProjectCreate, ProjectUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import project_dict
from ..services.audit import write_audit

router = APIRouter(prefix="/api/research-projects", tags=["科研项目"])


@router.get("", summary="科研项目列表")
def list_projects(
    teacher_id: int | None = None,
    college: str | None = None,
    discipline: str | None = None,
    level: str | None = None,
    status: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchProject)
    if teacher_id:
        member_ids = {
            r[0] for r in db.query(ProjectMember.project_id)
            .filter(ProjectMember.teacher_id == teacher_id).all()
        }
        if member_ids:
            query = query.filter(or_(
                ResearchProject.principal_teacher_id == teacher_id,
                ResearchProject.id.in_(member_ids),
            ))
        else:
            query = query.filter(ResearchProject.principal_teacher_id == teacher_id)
    if college or discipline:
        query = query.join(Teacher, ResearchProject.principal_teacher_id == Teacher.id)
        if college:
            query = query.filter(Teacher.college == college)
        if discipline:
            query = query.filter(Teacher.discipline == discipline)
    if level:
        query = query.filter(ResearchProject.level == level)
    if status:
        query = query.filter(ResearchProject.status == status)
    if year_from:
        query = query.filter(ResearchProject.start_date >= date(year_from, 1, 1))
    if year_to:
        query = query.filter(ResearchProject.start_date <= date(year_to, 12, 31))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            ResearchProject.name.like(pattern),
            ResearchProject.project_no.like(pattern),
        ))
    total = query.count()
    rows = (
        query.options(joinedload(ResearchProject.principal), joinedload(ResearchProject.members))
        .order_by(ResearchProject.start_date.desc(), ResearchProject.id.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return {"items": [project_dict(r) for r in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.get("/{project_id}", summary="项目详情")
def get_project(project_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    row = db.get(ResearchProject, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project_dict(row)


@router.post("", summary="新增科研项目")
def create_project(payload: ProjectCreate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if db.query(ResearchProject).filter(ResearchProject.project_no == payload.project_no).first():
        raise HTTPException(status_code=400, detail="项目编号已存在")
    principal = db.get(Teacher, payload.principal_teacher_id)
    if not principal:
        raise HTTPException(status_code=400, detail="负责人不存在")
    data = payload.model_dump()
    member_ids = data.pop("member_ids", [])
    if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
        raise HTTPException(status_code=400, detail="项目开始时间不能晚于结束时间")
    row = ResearchProject(**data)
    db.add(row)
    db.flush()
    member_set = {payload.principal_teacher_id, *member_ids}
    for teacher_id in member_set:
        if not db.get(Teacher, teacher_id):
            raise HTTPException(status_code=400, detail=f"项目成员教师 ID {teacher_id} 不存在")
        db.add(ProjectMember(
            project_id=row.id, teacher_id=teacher_id,
            role="主持人" if teacher_id == payload.principal_teacher_id else "参与人",
            contribution_pct=0,
        ))
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "research_project", row.id,
                f"新增项目 {row.project_no}《{row.name}》", client_ip(request))
    return project_dict(row)


@router.put("/{project_id}", summary="修改科研项目")
def update_project(project_id: int, payload: ProjectUpdate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ResearchProject, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    data = payload.model_dump(exclude_unset=True)
    member_ids = data.pop("member_ids", None)
    if "project_no" in data and data["project_no"] != row.project_no:
        if db.query(ResearchProject).filter(
            ResearchProject.project_no == data["project_no"]
        ).first():
            raise HTTPException(status_code=400, detail="项目编号已存在")
    start = data.get("start_date", row.start_date)
    end = data.get("end_date", row.end_date)
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="项目开始时间不能晚于结束时间")
    if "principal_teacher_id" in data and not db.get(Teacher, data["principal_teacher_id"]):
        raise HTTPException(status_code=400, detail="负责人不存在")
    for key, value in data.items():
        setattr(row, key, value)
    if member_ids is not None:
        db.query(ProjectMember).filter(ProjectMember.project_id == row.id).delete()
        ids = {row.principal_teacher_id, *member_ids}
        for teacher_id in ids:
            if not db.get(Teacher, teacher_id):
                raise HTTPException(status_code=400, detail=f"项目成员教师 ID {teacher_id} 不存在")
            db.add(ProjectMember(
                project_id=row.id, teacher_id=teacher_id,
                role="主持人" if teacher_id == row.principal_teacher_id else "参与人",
                contribution_pct=0,
            ))
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "research_project", row.id,
                f"修改项目 {row.project_no}", client_ip(request))
    return project_dict(row)


@router.delete("/{project_id}", summary="删除科研项目")
def delete_project(project_id: int, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(ResearchProject, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    name = row.name
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "research_project", project_id,
                f"删除项目《{name}》", client_ip(request))
    return {"message": "项目已删除"}
