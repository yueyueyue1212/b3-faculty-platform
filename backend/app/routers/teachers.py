from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AdvisorMatchResult,
    ProjectMember,
    ResearchOutput,
    ResearchProject,
    ServiceRecord,
    Teacher,
    TeachingRecord,
    User,
)
from ..schemas import TeacherCreate, TeacherUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import teacher_dict
from ..services.audit import write_audit
from ..services.directory import group_disciplines_by_college
from ..services.llm import generate_profile_summary, llm_public_status
from ..services.profile import build_teacher_profile

router = APIRouter(prefix="/api/teachers", tags=["教师档案"])

SORT_FIELDS = {
    "name": Teacher.name,
    "teacher_no": Teacher.teacher_no,
    "college": Teacher.college,
    "title": Teacher.title,
    "hire_date": Teacher.hire_date,
    "updated_at": Teacher.updated_at,
}


@router.get("", summary="教师列表（搜索/筛选/分页）")
def list_teachers(
    keyword: str | None = None,
    college: str | None = None,
    discipline: str | None = None,
    title: str | None = None,
    status: str | None = None,
    advisor_qualified: bool | None = None,
    enrollment_status: str | None = None,
    verification_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    sort_by: str = "teacher_no",
    sort_order: str = "asc",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Teacher)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            Teacher.name.like(pattern),
            Teacher.teacher_no.like(pattern),
            Teacher.research_direction.like(pattern),
            Teacher.research_keywords.like(pattern),
            Teacher.college.like(pattern),
            Teacher.discipline.like(pattern),
        ))
    if college:
        query = query.filter(Teacher.college == college)
    if discipline:
        query = query.filter(Teacher.discipline == discipline)
    if title:
        query = query.filter(Teacher.title == title)
    if status:
        query = query.filter(Teacher.status == status)
    if advisor_qualified is not None:
        query = query.filter(Teacher.advisor_qualified.is_(advisor_qualified))
    if enrollment_status:
        query = query.filter(Teacher.enrollment_status == enrollment_status)
    if verification_status:
        query = query.filter(Teacher.verification_status == verification_status)

    total = query.count()
    column = SORT_FIELDS.get(sort_by, Teacher.teacher_no)
    query = query.order_by(column.desc() if sort_order == "desc" else column.asc())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [teacher_dict(t, user) for t in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/options", summary="教师筛选选项")
def teacher_options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Teacher).all()
    return {
        "colleges": sorted({t.college for t in rows if t.college}),
        "disciplines": sorted({t.discipline for t in rows if t.discipline}),
        "disciplines_by_college": group_disciplines_by_college(rows),
        "titles": sorted({t.title for t in rows if t.title}),
        "degrees": sorted({t.degree for t in rows if t.degree}),
        "departments": sorted({t.department for t in rows if t.department}),
    }


@router.post("", summary="新增教师")
def create_teacher(payload: TeacherCreate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if db.query(Teacher).filter(Teacher.teacher_no == payload.teacher_no).first():
        raise HTTPException(status_code=400, detail="教师编号已存在")
    data = payload.model_dump()
    if data.get("capacity", 0) < data.get("current_students", 0):
        raise HTTPException(status_code=400, detail="指导容量不能小于当前在读人数")
    teacher = Teacher(**data)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    write_audit(db, user, "create", "teacher", teacher.id,
                f"新增教师 {teacher.teacher_no} {teacher.name}", client_ip(request))
    return teacher_dict(teacher, user)


@router.get("/{teacher_id}", summary="教师详情")
def get_teacher(teacher_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    data = teacher_dict(teacher, user)
    data["counts"] = {
        "outputs": db.query(ResearchOutput).filter(ResearchOutput.teacher_id == teacher.id).count(),
        "teaching": db.query(TeachingRecord).filter(TeachingRecord.teacher_id == teacher.id).count(),
        "services": db.query(ServiceRecord).filter(ServiceRecord.teacher_id == teacher.id).count(),
        "projects": db.query(ResearchProject).filter(
            ResearchProject.principal_teacher_id == teacher.id
        ).count(),
    }
    return data


@router.put("/{teacher_id}", summary="修改教师档案")
def update_teacher(teacher_id: int, payload: TeacherUpdate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    data = payload.model_dump(exclude_unset=True)
    if "teacher_no" in data and data["teacher_no"] != teacher.teacher_no:
        if db.query(Teacher).filter(Teacher.teacher_no == data["teacher_no"]).first():
            raise HTTPException(status_code=400, detail="教师编号已存在")
    capacity = data.get("capacity", teacher.capacity)
    current = data.get("current_students", teacher.current_students)
    if capacity is not None and current is not None and capacity < current:
        raise HTTPException(status_code=400, detail="指导容量不能小于当前在读人数")
    for key, value in data.items():
        setattr(teacher, key, value)
    db.commit()
    db.refresh(teacher)
    write_audit(db, user, "update", "teacher", teacher.id,
                f"修改教师 {teacher.teacher_no}，字段：{', '.join(data.keys()) or '无'}",
                client_ip(request))
    return teacher_dict(teacher, user)


@router.delete("/{teacher_id}", summary="删除教师（有关联记录时禁止）")
def delete_teacher(teacher_id: int, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    dependencies = {
        "科研成果": db.query(ResearchOutput).filter(ResearchOutput.teacher_id == teacher.id).count(),
        "教学记录": db.query(TeachingRecord).filter(TeachingRecord.teacher_id == teacher.id).count(),
        "社会服务": db.query(ServiceRecord).filter(ServiceRecord.teacher_id == teacher.id).count(),
        "主持项目": db.query(ResearchProject).filter(
            ResearchProject.principal_teacher_id == teacher.id
        ).count(),
        "项目参与": db.query(ProjectMember).filter(ProjectMember.teacher_id == teacher.id).count(),
    }
    active = {k: v for k, v in dependencies.items() if v}
    if active:
        detail = "、".join(f"{k}{v}条" for k, v in active.items())
        raise HTTPException(
            status_code=409,
            detail=f"该教师仍关联{detail}，为避免孤立记录不能删除；可先将状态改为退休/停用。",
        )
    db.query(AdvisorMatchResult).filter(AdvisorMatchResult.teacher_id == teacher.id).delete()
    db.delete(teacher)
    db.commit()
    write_audit(db, user, "delete", "teacher", teacher_id,
                f"删除教师 {teacher.teacher_no} {teacher.name}", client_ip(request))
    return {"message": "教师已删除"}


@router.get("/{teacher_id}/profile", summary="教师多维画像（数据库实时统计）")
def teacher_profile(teacher_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    profile = build_teacher_profile(db, teacher)
    profile["llm_status"] = llm_public_status()
    profile["sensitive_hidden"] = user.role == "viewer"
    return profile


@router.post("/{teacher_id}/ai-summary", summary="生成画像摘要（可选 LLM，无 Key 自动本地）")
def ai_summary(teacher_id: int, request: Request, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")
    profile = build_teacher_profile(db, teacher)
    result = generate_profile_summary(profile)
    write_audit(db, user, "ai_summary", "teacher", teacher.id,
                f"生成画像摘要，模式：{result['mode']}", client_ip(request))
    return {
        "teacher_id": teacher_id,
        "text": result["text"],
        "mode": result["mode"],
        "warning": result["warning"],
        "basis": {
            "output_count": profile["output_count"],
            "project_count": profile["project_count"],
            "completeness": profile["completeness"],
            "sensitive_data_sent": False,
        },
    }
