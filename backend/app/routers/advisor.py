import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import DEFAULT_ADVISOR_WEIGHTS
from ..database import get_db
from ..models import (
    AdvisorMatchResult,
    AdvisorMatchTask,
    StudentProfile,
    SystemSetting,
    Teacher,
    User,
)
from ..schemas import MatchScoreRequest, MatchTaskCreate, StudentCreate, StudentUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import match_result_dict, student_dict, task_dict, teacher_dict
from ..services.audit import write_audit
from ..services.matching import MATCH_GRADE_RULES, advisor_match, match_grade, normalize_weights
from ..utils import utcnow

router = APIRouter(prefix="/api/advisor", tags=["导师匹配"])
students_router = APIRouter(prefix="/api/students", tags=["学生需求"])


class ConfirmResult(BaseModel):
    human_confirmed: bool = True
    note: str | None = None


def _configured_weights(db: Session, raw: dict | None = None) -> dict:
    setting = db.query(SystemSetting).filter(SystemSetting.key == "advisor_weights").first()
    base = DEFAULT_ADVISOR_WEIGHTS
    if setting:
        try:
            base = json.loads(setting.value)
        except (TypeError, json.JSONDecodeError):
            base = DEFAULT_ADVISOR_WEIGHTS
    try:
        return normalize_weights(raw or base, DEFAULT_ADVISOR_WEIGHTS, set(DEFAULT_ADVISOR_WEIGHTS))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@students_router.get("", summary="学生需求档案列表")
def list_students(
    keyword: str | None = None,
    discipline: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(StudentProfile)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            StudentProfile.name.like(pattern),
            StudentProfile.student_no.like(pattern),
            StudentProfile.research_interest.like(pattern),
            StudentProfile.keywords.like(pattern),
            StudentProfile.desired_direction.like(pattern),
        ))
    if discipline:
        query = query.filter(StudentProfile.discipline == discipline)
    total = query.count()
    rows = (query.order_by(StudentProfile.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return {"items": [student_dict(r) for r in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@students_router.post("", summary="新增学生需求档案")
def create_student(payload: StudentCreate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if db.query(StudentProfile).filter(StudentProfile.student_no == payload.student_no).first():
        raise HTTPException(status_code=400, detail="学生编号已存在")
    row = StudentProfile(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "student_profile", row.id,
                f"新增学生需求 {row.student_no} {row.name}", client_ip(request))
    return student_dict(row)


@students_router.put("/{student_id}", summary="修改学生需求档案")
def update_student(student_id: int, payload: StudentUpdate, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(StudentProfile, student_id)
    if not row:
        raise HTTPException(status_code=404, detail="学生档案不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "student_profile", row.id,
                f"修改学生需求 {row.student_no}", client_ip(request))
    return student_dict(row)


@students_router.delete("/{student_id}", summary="删除学生需求档案")
def delete_student(student_id: int, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(StudentProfile, student_id)
    if not row:
        raise HTTPException(status_code=404, detail="学生档案不存在")
    task_count = db.query(AdvisorMatchTask).filter(AdvisorMatchTask.student_id == student_id).count()
    if task_count:
        raise HTTPException(status_code=409, detail=f"该学生已有 {task_count} 个匹配任务，不能删除")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "student_profile", student_id,
                f"删除学生需求 {row.student_no}", client_ip(request))
    return {"message": "学生档案已删除"}


@router.get("/weights", summary="默认匹配权重")
def default_weights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "advisor_weights").first()
    weights = DEFAULT_ADVISOR_WEIGHTS
    if setting:
        try:
            weights = normalize_weights(json.loads(setting.value), DEFAULT_ADVISOR_WEIGHTS,
                                        set(DEFAULT_ADVISOR_WEIGHTS))
        except (ValueError, json.JSONDecodeError):
            weights = DEFAULT_ADVISOR_WEIGHTS
    return {
        "weights": weights,
        "labels": {
            "direction": "研究方向相似度",
            "topic": "具体主题匹配度",
            "needs": "培养需求匹配度",
            "capacity": "指导容量适配度",
        },
    }


@router.post("/score", summary="师生匹配度量化（单教师或全体教师）")
def quantify_match(
    payload: MatchScoreRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Quantify teacher-student fit on a 0-100 scale without persisting a task.

    The score reuses the same explainable dimensions and hard-condition checks as
    advisor matching, so a teacher who fails eligibility is flagged even when the
    archival similarity score is high.
    """
    student = db.get(StudentProfile, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生档案不存在")

    teacher = None
    if payload.teacher_id is not None:
        teacher = db.get(Teacher, payload.teacher_id)
        if not teacher:
            raise HTTPException(status_code=404, detail="教师档案不存在")

    weights = _configured_weights(db, payload.weights)
    result = advisor_match(db, student, weights)
    rows = result["qualified"] + result["excluded"]
    if teacher is not None:
        rows = [row for row in rows if row["teacher"].id == teacher.id]

    items = []
    for row in rows:
        total = float(row["total_score"] or 0)
        grade = match_grade(total)
        contribution_values = {
            "direction": round(float(row["direction_score"]) * weights["direction"], 1),
            "topic": round(float(row["topic_score"]) * weights["topic"], 1),
            "needs": round(float(row["need_score"]) * weights["needs"], 1),
            "capacity": round(float(row["capacity_score"]) * weights["capacity"], 1),
        }
        dimensions = {}
        for key, value in contribution_values.items():
            score_key = "need_score" if key == "needs" else f"{key}_score"
            dimensions[key] = {
                "label": result["weight_labels"][key],
                "score": float(row[score_key]),
                "weight": weights[key],
                "contribution": value,
            }
        formula = (
            f"总分 {total:.1f} = 研究方向 {contribution_values['direction']:.1f}"
            f" + 具体主题 {contribution_values['topic']:.1f}"
            f" + 培养需求 {contribution_values['needs']:.1f}"
            f" + 容量适配 {contribution_values['capacity']:.1f}"
        )
        items.append({
            "teacher_id": row["teacher"].id,
            "teacher": teacher_dict(row["teacher"], user),
            "total_score": total,
            "grade": grade["grade"],
            "grade_label": grade["label"],
            "grade_description": grade["description"],
            "qualified": bool(row["qualified"]),
            "disqualifiers": row["disqualifiers"],
            "rank": row.get("rank"),
            "dimensions": dimensions,
            "formula": formula,
            "matched_terms": row.get("matched_terms") or [],
            "reasons": row["reasons"],
        })

    items.sort(key=lambda item: (not item["qualified"], -item["total_score"]))
    scores = [item["total_score"] for item in items]
    qualified_items = [item for item in items if item["qualified"]]
    best = qualified_items[0] if qualified_items else None
    return {
        "scope": "single" if teacher is not None else "all",
        "student": student_dict(student),
        "target_teacher_id": teacher.id if teacher is not None else None,
        "weights": weights,
        "weight_labels": result["weight_labels"],
        "grade_rules": MATCH_GRADE_RULES,
        "items": items,
        "summary": {
            "teacher_count": len(items),
            "qualified_count": len(qualified_items),
            "excluded_count": len(items) - len(qualified_items),
            "highest_score": round(max(scores), 1) if scores else None,
            "highest_qualified_score": round(qualified_items[0]["total_score"], 1) if qualified_items else None,
            "average_score": round(sum(scores) / len(scores), 1) if scores else None,
            "best_teacher": (
                {
                    "teacher_id": best["teacher_id"],
                    "name": best["teacher"]["name"],
                    "total_score": best["total_score"],
                    "grade": best["grade"],
                }
                if best else None
            ),
        },
        "note": (
            "匹配度为档案字段的规则量化结果，取值范围 0-100，仅供辅助参考，"
            "不代表真实培养效果或录取结论。未满足导师资格、招生状态或指导容量的教师"
            "即使得分较高也不会作为有效推荐；示例分级阈值仅用于演示。"
        ),
    }


@router.get("/tasks", summary="导师匹配任务列表")
def list_tasks(
    student_id: int | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(AdvisorMatchTask)
    if student_id:
        query = query.filter(AdvisorMatchTask.student_id == student_id)
    if status:
        query = query.filter(AdvisorMatchTask.status == status)
    total = query.count()
    rows = (query.order_by(AdvisorMatchTask.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = []
    for row in rows:
        item = task_dict(row)
        item["qualified_count"] = db.query(AdvisorMatchResult).filter(
            AdvisorMatchResult.task_id == row.id, AdvisorMatchResult.qualified.is_(True)
        ).count()
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.post("/tasks", summary="创建导师匹配任务")
def create_task(payload: MatchTaskCreate, request: Request,
                user: User = Depends(require_editor), db: Session = Depends(get_db)):
    student = db.get(StudentProfile, payload.student_id)
    if not student:
        raise HTTPException(status_code=400, detail="学生档案不存在")
    setting = db.query(SystemSetting).filter(SystemSetting.key == "advisor_weights").first()
    base = DEFAULT_ADVISOR_WEIGHTS
    if setting:
        try:
            base = json.loads(setting.value)
        except json.JSONDecodeError:
            pass
    try:
        weights = normalize_weights(payload.weights or base, DEFAULT_ADVISOR_WEIGHTS,
                                    set(DEFAULT_ADVISOR_WEIGHTS))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    task = AdvisorMatchTask(
        student_id=student.id,
        name=payload.name or f"{student.name} 导师匹配",
        weights=json.dumps(weights),
        status="pending",
        created_by=user.username,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    write_audit(db, user, "create", "advisor_match_task", task.id,
                f"创建导师匹配任务：{task.name}", client_ip(request))
    return task_dict(task)


@router.post("/tasks/{task_id}/run", summary="执行导师匹配（规则+TF-IDF）")
def run_task(task_id: int, request: Request,
             user: User = Depends(require_editor), db: Session = Depends(get_db)):
    task = db.get(AdvisorMatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="匹配任务不存在")
    student = db.get(StudentProfile, task.student_id)
    if not student:
        raise HTTPException(status_code=400, detail="学生档案不存在")
    task.status = "running"
    db.commit()
    try:
        weights = json.loads(task.weights)
        result = advisor_match(db, student, weights)
        db.query(AdvisorMatchResult).filter(AdvisorMatchResult.task_id == task.id).delete()
        db.flush()
        for row in result["qualified"] + result["excluded"]:
            db.add(AdvisorMatchResult(
                task_id=task.id,
                teacher_id=row["teacher"].id,
                total_score=row["total_score"],
                direction_score=row["direction_score"],
                topic_score=row["topic_score"],
                need_score=row["need_score"],
                capacity_score=row["capacity_score"],
                qualified=row["qualified"],
                reasons=row["reasons"],
                disqualifiers=row["disqualifiers"],
                rank=row.get("rank"),
            ))
        task.status = "completed"
        task.error = None
        task.completed_at = utcnow()
        db.commit()
        write_audit(db, user, "run", "advisor_match_task", task.id,
                    f"执行匹配任务，有效推荐 {result['summary']['qualified_count']} 人",
                    client_ip(request))
        return {
            **task_dict(task),
            "summary": result["summary"],
            "weight_labels": result["weight_labels"],
        }
    except Exception as exc:
        db.rollback()
        task = db.get(AdvisorMatchTask, task_id)
        task.status = "failed"
        task.error = str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"匹配执行失败：{exc}")


@router.get("/tasks/{task_id}", summary="导师匹配结果")
def get_task(task_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    task = db.get(AdvisorMatchTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="匹配任务不存在")
    results = (db.query(AdvisorMatchResult)
               .filter(AdvisorMatchResult.task_id == task.id)
               .order_by(AdvisorMatchResult.qualified.desc(),
                         AdvisorMatchResult.total_score.desc())
               .all())
    qualified = [match_result_dict(r) for r in results if r.qualified]
    excluded = [match_result_dict(r) for r in results if not r.qualified]
    data = task_dict(task)
    data["recommendations"] = qualified
    data["excluded"] = excluded
    data["summary"] = {
        "qualified_count": len(qualified),
        "excluded_count": len(excluded),
        "note": "仅满足导师资格、招生状态、指导容量的候选教师进入有效推荐排序；"
                "不满足硬性条件的教师即使规则分高也不会进入推荐。",
    }
    return data


@router.put("/results/{result_id}/confirm", summary="记录人工确认结果")
def confirm_result(result_id: int, payload: ConfirmResult, request: Request,
                   user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(AdvisorMatchResult, result_id)
    if not row:
        raise HTTPException(status_code=404, detail="匹配结果不存在")
    row.human_confirmed = payload.human_confirmed
    row.note = payload.note
    db.commit()
    write_audit(db, user, "confirm", "advisor_match_result", result_id,
                f"人工确认：{'确认' if payload.human_confirmed else '取消确认'}；备注：{payload.note or ''}",
                client_ip(request))
    return match_result_dict(row)
