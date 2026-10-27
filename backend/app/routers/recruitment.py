import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import DEFAULT_CANDIDATE_WEIGHTS
from ..database import get_db
from ..models import CandidateEvaluation, CandidateProfile, JobPosition, User
from ..schemas import CandidateCreate, CandidateUpdate, EvaluationReview, PositionCreate, PositionUpdate
from ..security import client_ip, get_current_user, require_editor
from ..serializers import candidate_dict, evaluation_dict, position_dict
from ..services.audit import write_audit
from ..services.matching import evaluate_position, normalize_weights

router = APIRouter(prefix="/api/recruitment", tags=["人才引进"])


def _position_weights(raw) -> dict:
    try:
        return normalize_weights(raw, DEFAULT_CANDIDATE_WEIGHTS, set(DEFAULT_CANDIDATE_WEIGHTS))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/positions", summary="招聘岗位列表")
def list_positions(
    keyword: str | None = None,
    college: str | None = None,
    discipline: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(JobPosition)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            JobPosition.name.like(pattern),
            JobPosition.research_direction.like(pattern),
            JobPosition.research_topics.like(pattern),
        ))
    if college:
        query = query.filter(JobPosition.college == college)
    if discipline:
        query = query.filter(JobPosition.discipline == discipline)
    if status:
        query = query.filter(JobPosition.status == status)
    rows = query.order_by(JobPosition.id.desc()).all()
    items = []
    for row in rows:
        item = position_dict(row)
        item["candidate_count"] = db.query(CandidateProfile).filter(
            CandidateProfile.position_id == row.id
        ).count()
        item["evaluated_count"] = db.query(CandidateEvaluation).filter(
            CandidateEvaluation.position_id == row.id
        ).count()
        items.append(item)
    return {"items": items, "total": len(items)}


@router.post("/positions", summary="新增招聘岗位")
def create_position(payload: PositionCreate, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    data = payload.model_dump()
    weights = _position_weights(data.pop("weights", None))
    row = JobPosition(**data, weights=json.dumps(weights))
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "job_position", row.id,
                f"新增招聘岗位 {row.name}", client_ip(request))
    return position_dict(row)


@router.put("/positions/{position_id}", summary="修改招聘岗位")
def update_position(position_id: int, payload: PositionUpdate, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(JobPosition, position_id)
    if not row:
        raise HTTPException(status_code=404, detail="招聘岗位不存在")
    data = payload.model_dump(exclude_unset=True)
    if "weights" in data:
        weights = _position_weights(data.pop("weights"))
        row.weights = json.dumps(weights)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "job_position", row.id,
                f"修改招聘岗位 {row.name}", client_ip(request))
    return position_dict(row)


@router.delete("/positions/{position_id}", summary="删除招聘岗位")
def delete_position(position_id: int, request: Request,
                    user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(JobPosition, position_id)
    if not row:
        raise HTTPException(status_code=404, detail="招聘岗位不存在")
    candidates = db.query(CandidateProfile).filter(CandidateProfile.position_id == position_id).count()
    if candidates:
        raise HTTPException(status_code=409, detail=f"该岗位已有 {candidates} 名候选人，不能删除")
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "job_position", position_id,
                f"删除招聘岗位 {row.name}", client_ip(request))
    return {"message": "岗位已删除"}


@router.get("/candidates", summary="候选人档案列表")
def list_candidates(
    position_id: int | None = None,
    keyword: str | None = None,
    degree: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(CandidateProfile)
    if position_id:
        query = query.filter(CandidateProfile.position_id == position_id)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(or_(
            CandidateProfile.name.like(pattern),
            CandidateProfile.major.like(pattern),
            CandidateProfile.research_direction.like(pattern),
            CandidateProfile.keywords.like(pattern),
        ))
    if degree:
        query = query.filter(CandidateProfile.degree == degree)
    total = query.count()
    rows = (query.order_by(CandidateProfile.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return {"items": [candidate_dict(r) for r in rows], "total": total, "page": page,
            "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@router.post("/candidates", summary="新增候选人档案")
def create_candidate(payload: CandidateCreate, request: Request,
                     user: User = Depends(require_editor), db: Session = Depends(get_db)):
    if not db.get(JobPosition, payload.position_id):
        raise HTTPException(status_code=400, detail="关联岗位不存在")
    row = CandidateProfile(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "create", "candidate_profile", row.id,
                f"新增候选人 {row.name}", client_ip(request))
    return candidate_dict(row)


@router.put("/candidates/{candidate_id}", summary="修改候选人档案")
def update_candidate(candidate_id: int, payload: CandidateUpdate, request: Request,
                     user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(CandidateProfile, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="候选人档案不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    write_audit(db, user, "update", "candidate_profile", row.id,
                f"修改候选人 {row.name}", client_ip(request))
    return candidate_dict(row)


@router.delete("/candidates/{candidate_id}", summary="删除候选人档案")
def delete_candidate(candidate_id: int, request: Request,
                     user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(CandidateProfile, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="候选人档案不存在")
    db.query(CandidateEvaluation).filter(
        CandidateEvaluation.candidate_id == candidate_id
    ).delete()
    name = row.name
    db.delete(row)
    db.commit()
    write_audit(db, user, "delete", "candidate_profile", candidate_id,
                f"删除候选人 {name}", client_ip(request))
    return {"message": "候选人档案已删除"}


@router.get("/positions/{position_id}", summary="岗位详情")
def get_position(position_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    row = db.get(JobPosition, position_id)
    if not row:
        raise HTTPException(status_code=404, detail="招聘岗位不存在")
    data = position_dict(row)
    data["candidate_count"] = db.query(CandidateProfile).filter(
        CandidateProfile.position_id == position_id
    ).count()
    return data


@router.post("/positions/{position_id}/evaluate", summary="执行岗位—候选人匹配评估")
def evaluate(position_id: int, request: Request,
             user: User = Depends(require_editor), db: Session = Depends(get_db)):
    position = db.get(JobPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="招聘岗位不存在")
    candidates = db.query(CandidateProfile).filter(
        CandidateProfile.position_id == position_id
    ).count()
    if not candidates:
        raise HTTPException(status_code=400, detail="该岗位暂无候选人，无法评估")
    evaluations = evaluate_position(db, position)
    write_audit(db, user, "evaluate", "job_position", position_id,
                f"执行岗位匹配，候选人数 {candidates}", client_ip(request))
    return {
        "position": position_dict(position),
        "items": [evaluation_dict(e) for e in evaluations],
        "summary": {
            "total": len(evaluations),
            "hard_pass": sum(1 for e in evaluations if e.hard_pass),
            "hard_fail": sum(1 for e in evaluations if not e.hard_pass),
            "note": "系统仅提供辅助评估建议，不自动作出录用或淘汰决定。",
        },
    }


@router.get("/positions/{position_id}/evaluations", summary="岗位评估结果")
def position_evaluations(position_id: int, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    position = db.get(JobPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="招聘岗位不存在")
    rows = (db.query(CandidateEvaluation)
            .filter(CandidateEvaluation.position_id == position_id)
            .order_by(CandidateEvaluation.hard_pass.desc(),
                      CandidateEvaluation.total_score.desc())
            .all())
    return {
        "position": position_dict(position),
        "items": [evaluation_dict(e) for e in rows],
        "summary": {
            "total": len(rows),
            "hard_pass": sum(1 for e in rows if e.hard_pass),
            "hard_fail": sum(1 for e in rows if not e.hard_pass),
            "note": "系统仅提供辅助评估建议，不自动作出录用或淘汰决定；"
                    "评审状态由人工填写。",
        },
    }


@router.put("/evaluations/{evaluation_id}/review", summary="人工评审意见")
def review_evaluation(evaluation_id: int, payload: EvaluationReview, request: Request,
                      user: User = Depends(require_editor), db: Session = Depends(get_db)):
    row = db.get(CandidateEvaluation, evaluation_id)
    if not row:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    row.review_status = payload.review_status
    row.review_note = payload.review_note
    row.reviewer = user.username
    db.commit()
    db.refresh(row)
    write_audit(db, user, "review", "candidate_evaluation", row.id,
                f"人工评审：{row.review_status}；备注：{row.review_note or ''}",
                client_ip(request))
    return evaluation_dict(row)
