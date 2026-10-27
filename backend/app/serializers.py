import json
from datetime import date

from .models import (
    AdvisorMatchResult,
    AdvisorMatchTask,
    CandidateEvaluation,
    CandidateProfile,
    JobPosition,
    PromotionMaterial,
    PromotionRequirement,
    ResearchOutput,
    ResearchProject,
    ServiceRecord,
    StudentProfile,
    Teacher,
    TeachingRecord,
    User,
)
from .utils import masked

OUTPUT_TYPE_LABELS = {"paper": "论文", "patent": "专利", "book": "著作", "report": "研究报告"}
SERVICE_TYPE_LABELS = {"award": "获奖", "academic_post": "学术任职", "social_service": "社会服务"}
TEACHER_STATUS_LABELS = {"active": "在职", "on_leave": "休假/进修", "retired": "退休"}
ENROLLMENT_LABELS = {"open": "开放招生", "full": "已满", "closed": "未开放"}
ROLE_LABELS = {"admin": "管理员", "manager": "业务人员", "viewer": "只读用户"}


def user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def teacher_dict(teacher: Teacher, user: User | None = None) -> dict:
    is_viewer = user is not None and user.role == "viewer"
    phone = teacher.phone
    email = teacher.email
    if is_viewer:
        phone = masked(phone)
        email = masked(email)
    return {
        "id": teacher.id,
        "teacher_no": teacher.teacher_no,
        "name": teacher.name,
        "gender": teacher.gender,
        "birth_year": teacher.birth_year,
        "age": (date.today().year - teacher.birth_year) if teacher.birth_year else None,
        "college": teacher.college,
        "department": teacher.department,
        "discipline": teacher.discipline,
        "degree": teacher.degree,
        "title": teacher.title,
        "position": teacher.position,
        "hire_date": teacher.hire_date.isoformat() if teacher.hire_date else None,
        "research_direction": teacher.research_direction,
        "bio": teacher.bio,
        "skills": teacher.skills,
        "research_keywords": teacher.research_keywords,
        "status": teacher.status,
        "status_label": TEACHER_STATUS_LABELS.get(teacher.status, teacher.status),
        "advisor_qualified": teacher.advisor_qualified,
        "enrollment_status": teacher.enrollment_status,
        "enrollment_label": ENROLLMENT_LABELS.get(teacher.enrollment_status, teacher.enrollment_status),
        "capacity": teacher.capacity,
        "current_students": teacher.current_students,
        "available_capacity": max(0, (teacher.capacity or 0) - (teacher.current_students or 0)),
        "phone": phone,
        "email": email,
        "phone_masked": is_viewer,
        "data_source": teacher.data_source,
        "verification_status": teacher.verification_status,
        "created_at": teacher.created_at.isoformat() if teacher.created_at else None,
        "updated_at": teacher.updated_at.isoformat() if teacher.updated_at else None,
    }


def output_dict(row: ResearchOutput) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "output_type": row.output_type,
        "output_type_label": OUTPUT_TYPE_LABELS.get(row.output_type, row.output_type),
        "title": row.title,
        "venue": row.venue,
        "publish_date": row.publish_date.isoformat() if row.publish_date else None,
        "level": row.level,
        "authors": row.authors,
        "doi": row.doi,
        "data_source": row.data_source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def project_dict(row: ResearchProject, include_members: bool = True) -> dict:
    data = {
        "id": row.id,
        "project_no": row.project_no,
        "name": row.name,
        "level": row.level,
        "funding": row.funding,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "principal_teacher_id": row.principal_teacher_id,
        "principal_name": row.principal.name if row.principal else None,
        "status": row.status,
        "data_source": row.data_source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if include_members:
        data["members"] = [
            {
                "id": m.id,
                "teacher_id": m.teacher_id,
                "teacher_name": m.teacher.name if m.teacher else None,
                "role": m.role,
                "contribution_pct": m.contribution_pct,
            }
            for m in row.members
        ]
    return data


def teaching_dict(row: TeachingRecord) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "course_name": row.course_name,
        "academic_year": row.academic_year,
        "semester": row.semester,
        "hours": row.hours,
        "student_count": row.student_count,
        "teaching_level": row.teaching_level,
        "evaluation_score": row.evaluation_score,
        "achievement": row.achievement,
        "data_source": row.data_source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def service_dict(row: ServiceRecord) -> dict:
    return {
        "id": row.id,
        "teacher_id": row.teacher_id,
        "service_type": row.service_type,
        "service_type_label": SERVICE_TYPE_LABELS.get(row.service_type, row.service_type),
        "name": row.name,
        "organization": row.organization,
        "role": row.role,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "description": row.description,
        "data_source": row.data_source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def student_dict(row: StudentProfile) -> dict:
    return {
        "id": row.id,
        "student_no": row.student_no,
        "name": row.name,
        "major": row.major,
        "discipline": row.discipline,
        "research_interest": row.research_interest,
        "keywords": row.keywords,
        "desired_direction": row.desired_direction,
        "training_needs": row.training_needs,
        "degree_goal": row.degree_goal,
        "other_conditions": row.other_conditions,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def match_result_dict(row: AdvisorMatchResult) -> dict:
    teacher = row.teacher
    return {
        "id": row.id,
        "task_id": row.task_id,
        "teacher_id": row.teacher_id,
        "teacher": teacher_dict(teacher) if teacher else None,
        "total_score": row.total_score,
        "direction_score": row.direction_score,
        "topic_score": row.topic_score,
        "need_score": row.need_score,
        "capacity_score": row.capacity_score,
        "qualified": row.qualified,
        "reasons": row.reasons,
        "disqualifiers": row.disqualifiers,
        "rank": row.rank,
        "human_confirmed": row.human_confirmed,
        "note": row.note,
    }


def task_dict(row: AdvisorMatchTask) -> dict:
    try:
        weights = json.loads(row.weights)
    except (TypeError, json.JSONDecodeError):
        weights = {}
    return {
        "id": row.id,
        "student_id": row.student_id,
        "student": student_dict(row.student) if row.student else None,
        "name": row.name,
        "weights": weights,
        "status": row.status,
        "created_by": row.created_by,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def requirement_dict(row: PromotionRequirement) -> dict:
    return {
        "id": row.id,
        "batch_id": row.batch_id,
        "category": row.category,
        "name": row.name,
        "requirement_desc": row.requirement_desc,
        "min_count": row.min_count,
        "mandatory": row.mandatory,
        "keywords": row.keywords,
        "window_years": row.window_years,
        "principal_only": row.principal_only,
    }


def material_dict(row: PromotionMaterial) -> dict:
    return {
        "id": row.id,
        "batch_id": row.batch_id,
        "teacher_id": row.teacher_id,
        "requirement_id": row.requirement_id,
        "category": row.category,
        "title": row.title,
        "output_type": row.output_type,
        "output_ref": row.output_ref,
        "matched_count": row.matched_count,
        "status": row.status,
        "note": row.note,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def position_dict(row: JobPosition) -> dict:
    try:
        weights = json.loads(row.weights) if row.weights else {}
    except (TypeError, json.JSONDecodeError):
        weights = {}
    return {
        "id": row.id,
        "name": row.name,
        "college": row.college,
        "discipline": row.discipline,
        "research_direction": row.research_direction,
        "required_degree": row.required_degree,
        "min_outputs": row.min_outputs,
        "research_topics": row.research_topics,
        "requirements_desc": row.requirements_desc,
        "weights": weights,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def candidate_dict(row: CandidateProfile) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "position_id": row.position_id,
        "position_name": row.position.name if row.position else None,
        "degree": row.degree,
        "graduate_school": row.graduate_school,
        "major": row.major,
        "research_direction": row.research_direction,
        "keywords": row.keywords,
        "outputs_count": row.outputs_count,
        "projects_count": row.projects_count,
        "teaching_years": row.teaching_years,
        "output_evidence": row.output_evidence,
        "project_evidence": row.project_evidence,
        "teaching_evidence": row.teaching_evidence,
        "source": row.source,
        "unverified_fields": row.unverified_fields,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def evaluation_dict(row: CandidateEvaluation) -> dict:
    return {
        "id": row.id,
        "candidate_id": row.candidate_id,
        "candidate": candidate_dict(row.candidate) if row.candidate else None,
        "position_id": row.position_id,
        "position_name": row.position.name if row.position else None,
        "hard_pass": row.hard_pass,
        "direction_score": row.direction_score,
        "outputs_score": row.outputs_score,
        "projects_score": row.projects_score,
        "teaching_score": row.teaching_score,
        "total_score": row.total_score,
        "rank": row.rank,
        "reasons": row.reasons,
        "gaps": row.gaps,
        "evidence": row.evidence,
        "review_status": row.review_status,
        "reviewer": row.reviewer,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
