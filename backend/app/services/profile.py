from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from ..models import ProjectMember, ResearchOutput, ResearchProject, ServiceRecord, Teacher, TeachingRecord
from ..utils import split_keywords

COMPLETENESS_FIELDS = [
    ("college", "学院"),
    ("discipline", "学科"),
    ("degree", "学历"),
    ("title", "职称"),
    ("hire_date", "入职时间"),
    ("research_direction", "研究方向"),
    ("research_keywords", "研究关键词"),
    ("bio", "个人简介"),
    ("skills", "专业技能"),
    ("email", "邮箱"),
    ("phone", "联系方式"),
]

OUTPUT_TYPE_LABELS = {"paper": "论文", "patent": "专利", "book": "著作", "report": "研究报告"}


def _year_of(value) -> int | None:
    if value is None:
        return None
    if hasattr(value, "year"):
        return value.year
    try:
        return int(str(value)[:4])
    except (ValueError, TypeError):
        return None


def build_teacher_profile(db: Session, teacher: Teacher) -> dict:
    outputs = db.query(ResearchOutput).filter(ResearchOutput.teacher_id == teacher.id).all()
    output_by_year = Counter()
    output_by_type = Counter()
    output_by_level = Counter()
    for item in outputs:
        year = _year_of(item.publish_date)
        if year:
            output_by_year[year] += 1
        output_by_type[item.output_type] += 1
        if item.level:
            output_by_level[item.level] += 1

    member_project_ids = {
        row[0]
        for row in db.query(ProjectMember.project_id).filter(ProjectMember.teacher_id == teacher.id).all()
    }
    projects = (
        db.query(ResearchProject)
        .filter(
            (ResearchProject.principal_teacher_id == teacher.id)
            | (ResearchProject.id.in_(member_project_ids))
        )
        .all()
        if member_project_ids
        else db.query(ResearchProject).filter(ResearchProject.principal_teacher_id == teacher.id).all()
    )
    principal_projects = [p for p in projects if p.principal_teacher_id == teacher.id]
    project_funding = round(sum((p.funding or 0) for p in projects), 2)
    project_by_year = Counter()
    for p in projects:
        year = _year_of(p.start_date)
        if year:
            project_by_year[year] += 1

    teaching = (
        db.query(TeachingRecord)
        .filter(TeachingRecord.teacher_id == teacher.id)
        .order_by(TeachingRecord.academic_year.desc())
        .all()
    )
    teaching_hours = round(sum((t.hours or 0) for t in teaching), 1)
    evaluation_scores = [t.evaluation_score for t in teaching if t.evaluation_score is not None]
    avg_eval = round(sum(evaluation_scores) / len(evaluation_scores), 1) if evaluation_scores else None
    teaching_by_year = Counter()
    for t in teaching:
        year = _year_of(t.academic_year)
        if year:
            teaching_by_year[year] += t.hours or 0

    services = (
        db.query(ServiceRecord)
        .filter(ServiceRecord.teacher_id == teacher.id)
        .order_by(ServiceRecord.start_date.desc())
        .all()
    )
    award_count = sum(1 for s in services if s.service_type == "award")
    academic_post_count = sum(1 for s in services if s.service_type == "academic_post")
    social_service_count = sum(1 for s in services if s.service_type == "social_service")

    missing_fields = [
        label for field, label in COMPLETENESS_FIELDS if not getattr(teacher, field, None)
    ]
    completeness = round(
        (len(COMPLETENESS_FIELDS) - len(missing_fields)) / len(COMPLETENESS_FIELDS) * 100, 1
    )

    recent_years = sorted(output_by_year.keys())[-3:]
    recent_outputs = sum(output_by_year[y] for y in recent_years)
    sci_count = sum(v for k, v in output_by_level.items() if k and ("SCI" in k.upper() or "SSCI" in k.upper()))

    tags = []
    if len(outputs) >= 8:
        tags.append("科研产出活跃")
    if sci_count >= 3:
        tags.append("高水平论文较多")
    if len(principal_projects) >= 2:
        tags.append("项目负责人")
    if teaching_hours >= 200:
        tags.append("教学工作量突出")
    if avg_eval is not None and avg_eval >= 90:
        tags.append("教学评价优秀")
    if award_count:
        tags.append("获奖经历")
    if academic_post_count:
        tags.append("学术任职")
    if teacher.advisor_qualified:
        tags.append("在招导师")
    if not outputs:
        tags.append("科研数据待补充")

    keywords = split_keywords(teacher.research_keywords)
    direction = teacher.research_direction or "未填写"
    year_span = f"{min(output_by_year)}–{max(output_by_year)}年" if output_by_year else "暂无年度数据"

    summary_parts = [
        f"该教师为{teacher.college}{teacher.discipline}{teacher.title}，研究方向为{direction}。",
        f"数据库已归集{year_span}科研/教学记录：成果{len(outputs)}项、项目{len(projects)}项（主持{len(principal_projects)}项）、"
        f"教学工作量{teaching_hours}学时、获奖{award_count}项。",
        f"档案数据完整度{completeness}%。",
    ]
    if not outputs:
        summary_parts.append("当前未关联科研产出记录，不能据此评价其科研能力。")
    if missing_fields:
        summary_parts.append(f"待补充字段：{'、'.join(missing_fields)}。")

    suggestions = []
    if not outputs:
        suggestions.append("先补全近五年论文、专利或著作记录，再生成科研维度评价。")
    if "研究关键词" in missing_fields or "研究方向" in missing_fields:
        suggestions.append("补充研究方向和关键词，可提升导师匹配与学科分析的准确度。")
    if missing_fields:
        suggestions.append(f"完善档案字段：{'、'.join(missing_fields[:5])}。")
    if len(recent_years) >= 2 and recent_outputs == 0:
        suggestions.append("近三年成果记录为空，建议核实是否漏录或调整研究方向。")
    if teacher.advisor_qualified and (teacher.capacity or 0) <= (teacher.current_students or 0):
        suggestions.append("导师指导容量已满，如有新增招生计划需调整容量。")
    if not suggestions:
        suggestions.append("档案与成果数据较为完整，建议定期核对数据来源与更新时间。")
    suggestions.append("以上结论仅基于数据库已归集数据，不构成对教师能力的确定性评价。")

    return {
        "teacher": {
            "id": teacher.id,
            "teacher_no": teacher.teacher_no,
            "name": teacher.name,
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
            "advisor_qualified": teacher.advisor_qualified,
            "enrollment_status": teacher.enrollment_status,
            "capacity": teacher.capacity,
            "current_students": teacher.current_students,
            "data_source": teacher.data_source,
            "verification_status": teacher.verification_status,
            "updated_at": teacher.updated_at.isoformat() if teacher.updated_at else None,
        },
        "research_direction": teacher.research_direction,
        "research_keywords": keywords,
        "title": teacher.title,
        "degree": teacher.degree,
        "output_count": len(outputs),
        "output_by_year": dict(sorted(output_by_year.items())),
        "output_by_type": {
            OUTPUT_TYPE_LABELS.get(k, k): v for k, v in output_by_type.items()
        },
        "output_by_level": dict(output_by_level),
        "recent_three_year_outputs": recent_outputs,
        "project_count": len(projects),
        "principal_project_count": len(principal_projects),
        "project_funding_total": project_funding,
        "project_by_year": dict(sorted(project_by_year.items())),
        "course_count": len({t.course_name for t in teaching}),
        "teaching_record_count": len(teaching),
        "teaching_hours_total": teaching_hours,
        "avg_evaluation_score": avg_eval,
        "teaching_achievement_count": sum(1 for t in teaching if t.achievement),
        "teaching_by_year": {str(k): round(v, 1) for k, v in sorted(teaching_by_year.items())},
        "service_count": len(services),
        "award_count": award_count,
        "academic_post_count": academic_post_count,
        "social_service_count": social_service_count,
        "tags": tags,
        "completeness": completeness,
        "missing_fields": missing_fields,
        "completeness_detail": [
            {"field": field, "label": label, "present": bool(getattr(teacher, field, None))}
            for field, label in COMPLETENESS_FIELDS
        ],
        "metric_definitions": [
            {"metric": "成果数量", "definition": "research_outputs 表中关联该教师的记录数", "source": "科研成果表"},
            {"metric": "项目数", "definition": "主持或作为成员参与的项目，按项目去重计数", "source": "科研项目表 + 项目成员表"},
            {"metric": "教学工作量", "definition": "teaching_records.hours 合计，按课程记录累加", "source": "教学记录表"},
            {"metric": "获奖数", "definition": "service_records 中 service_type=award 的记录数", "source": "社会服务表"},
            {"metric": "数据完整度", "definition": "11 项关键档案字段非空比例（不含敏感信息展示）", "source": "教师档案表"},
        ],
        "local_summary": "\n\n".join(
            ["【画像摘要】" + "".join(summary_parts), "【发展建议】" + "；".join(suggestions[:-1]) + "。" + suggestions[-1]]
        ),
        "last_updated": teacher.updated_at.isoformat() if teacher.updated_at else None,
        "data_source": teacher.data_source,
        "outputs": [
            {
                "id": o.id,
                "output_type": o.output_type,
                "output_type_label": OUTPUT_TYPE_LABELS.get(o.output_type, o.output_type),
                "title": o.title,
                "venue": o.venue,
                "publish_date": o.publish_date.isoformat() if o.publish_date else None,
                "level": o.level,
                "data_source": o.data_source,
            }
            for o in sorted(outputs, key=lambda x: (x.publish_date or __import__("datetime").date.min), reverse=True)[:20]
        ],
        "projects": [
            {
                "id": p.id,
                "project_no": p.project_no,
                "name": p.name,
                "level": p.level,
                "funding": p.funding,
                "role": "主持人" if p.principal_teacher_id == teacher.id else "参与人",
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "status": p.status,
            }
            for p in projects[:20]
        ],
        "teaching_records": [
            {
                "id": t.id,
                "course_name": t.course_name,
                "academic_year": t.academic_year,
                "semester": t.semester,
                "hours": t.hours,
                "evaluation_score": t.evaluation_score,
                "achievement": t.achievement,
            }
            for t in teaching[:20]
        ],
        "service_records": [
            {
                "id": s.id,
                "service_type": s.service_type,
                "name": s.name,
                "organization": s.organization,
                "role": s.role,
                "start_date": s.start_date.isoformat() if s.start_date else None,
            }
            for s in services[:20]
        ],
    }
