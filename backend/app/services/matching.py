"""Explainable rule-based matching for advisors and recruitment."""
import json
from datetime import date

from sqlalchemy.orm import Session

from ..config import DEFAULT_ADVISOR_WEIGHTS, DEFAULT_CANDIDATE_WEIGHTS
from ..models import (
    CandidateEvaluation,
    CandidateProfile,
    JobPosition,
    ResearchOutput,
    StudentProfile,
    Teacher,
)
from ..utils import split_keywords
from .text import keyword_match, tfidf_similarities

DEGREE_RANK = {"学士": 1, "本科": 1, "硕士": 2, "研究生": 2, "博士": 3, "博士后": 3}
WEIGHT_LABELS = {
    "direction": "研究方向相似度",
    "topic": "具体主题匹配度",
    "needs": "培养需求匹配度",
    "capacity": "指导容量适配度",
    "outputs": "科研成果",
    "projects": "项目经历",
    "teaching": "教学经历",
}

# Demo-only score bands. They quantify archive-field similarity for reference
# and must not be treated as a real university admission or placement rule.
MATCH_GRADE_RULES = [
    {
        "min_score": 55.0,
        "grade": "A",
        "label": "高度匹配",
        "description": "档案字段与培养需求高度契合，建议优先进行人工沟通确认。",
    },
    {
        "min_score": 40.0,
        "grade": "B",
        "label": "较高匹配",
        "description": "整体较契合，建议结合面谈、作品或面试材料进一步确认。",
    },
    {
        "min_score": 25.0,
        "grade": "C",
        "label": "中等匹配",
        "description": "存在部分契合点，需要人工判断方向差异与培养条件。",
    },
    {
        "min_score": 0.0,
        "grade": "D",
        "label": "低匹配",
        "description": "档案匹配证据较弱，建议补充方向、关键词或培养需求后再评估。",
    },
]


def match_grade(score: float) -> dict:
    """Return the demo score band for a 0-100 quantified match score."""
    safe_score = max(0.0, min(100.0, float(score or 0)))
    for rule in MATCH_GRADE_RULES:
        if safe_score >= rule["min_score"]:
            return dict(rule)
    return dict(MATCH_GRADE_RULES[-1])


def normalize_weights(raw, defaults: dict, allowed: set[str]) -> dict:
    merged = dict(defaults)
    if raw:
        for key, value in raw.items():
            if key not in allowed:
                raise ValueError(f"未知权重维度：{key}")
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"权重 {key} 必须是数字")
            if value < 0 or value > 100:
                raise ValueError(f"权重 {key} 必须在 0-100 之间")
            merged[key] = value
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("权重之和必须大于 0")
    return {key: round(value / total, 4) for key, value in merged.items()}


def _teacher_doc(teacher: Teacher, output_titles: list[str]) -> str:
    return " ".join(
        str(x)
        for x in [
            teacher.research_direction,
            teacher.research_keywords,
            teacher.bio,
            teacher.skills,
            " ".join(output_titles[:15]),
        ]
        if x
    )


def advisor_match(db: Session, student: StudentProfile, weights: dict) -> dict:
    weights = normalize_weights(weights, DEFAULT_ADVISOR_WEIGHTS, set(DEFAULT_ADVISOR_WEIGHTS))
    teachers = db.query(Teacher).order_by(Teacher.id).all()
    titles_by_teacher: dict[int, list[str]] = {}
    for teacher_id, title in db.query(ResearchOutput.teacher_id, ResearchOutput.title).all():
        titles_by_teacher.setdefault(teacher_id, []).append(title)

    docs = [_teacher_doc(t, titles_by_teacher.get(t.id, [])) for t in teachers]
    direction_query = " ".join(
        str(x) for x in [student.desired_direction, student.research_interest, student.keywords] if x
    )
    direction_scores = tfidf_similarities(direction_query, docs)

    need_query = " ".join(
        str(x) for x in [student.training_needs, student.degree_goal, student.other_conditions] if x
    )
    need_docs = [
        " ".join(str(x) for x in [t.skills, t.bio, t.research_direction] if x)
        for t in teachers
    ]
    need_scores = tfidf_similarities(need_query, need_docs)

    student_interest = "，".join(
        str(x) for x in [student.keywords, student.research_interest, student.desired_direction] if x
    )

    results = []
    for idx, teacher in enumerate(teachers):
        available = max(0, (teacher.capacity or 0) - (teacher.current_students or 0))
        disqualifiers = []
        if teacher.status != "active":
            disqualifiers.append(f"教师状态为“{teacher.status}”，非在职")
        if not teacher.advisor_qualified:
            disqualifiers.append("未取得导师指导资格")
        if teacher.enrollment_status != "open":
            disqualifiers.append(
                "招生状态为“已满”" if teacher.enrollment_status == "full" else "招生状态未开放"
            )
        if (teacher.capacity or 0) <= 0:
            disqualifiers.append("未配置指导容量")
        elif available <= 0:
            disqualifiers.append(
                f"指导容量已满（在读 {teacher.current_students}/{teacher.capacity}）"
            )

        direction_score = direction_scores[idx] if idx < len(direction_scores) else 0.0
        topic_score, matched_terms = keyword_match(
            student_interest,
            " ".join(str(x) for x in [teacher.research_keywords, teacher.research_direction] if x),
            titles_by_teacher.get(teacher.id, []),
        )
        need_score = need_scores[idx] if idx < len(need_scores) else 0.0
        capacity_score = round(available / teacher.capacity, 4) if (teacher.capacity or 0) > 0 else 0.0

        total = (
            direction_score * weights["direction"]
            + topic_score * weights["topic"]
            + need_score * weights["needs"]
            + capacity_score * weights["capacity"]
        ) * 100
        total = round(total, 1)

        reason_lines = [
            f"研究方向相似度 {direction_score * 100:.1f}%（TF-IDF：学生期望方向/兴趣 vs 导师方向、关键词、成果标题）",
            f"具体主题匹配度 {topic_score * 100:.1f}%"
            + (f"，命中兴趣词：{'、'.join(matched_terms)}" if matched_terms else "，未命中明确兴趣关键词"),
            f"培养需求匹配度 {need_score * 100:.1f}%（学生培养需求 vs 导师技能与简介）",
            f"指导容量适配度 {capacity_score * 100:.1f}%（剩余 {available}/{teacher.capacity}）",
            f"评分权重：研究方向 {weights['direction'] * 100:.0f}% · 主题 {weights['topic'] * 100:.0f}% · "
            f"培养需求 {weights['needs'] * 100:.0f}% · 容量 {weights['capacity'] * 100:.0f}%",
        ]
        if not teacher.research_keywords and not teacher.research_direction:
            reason_lines.append("导师研究方向数据缺失，方向相似度可能偏低，建议先补全画像。")

        results.append(
            {
                "teacher": teacher,
                "total_score": total,
                "direction_score": round(direction_score * 100, 1),
                "topic_score": round(topic_score * 100, 1),
                "need_score": round(need_score * 100, 1),
                "capacity_score": round(capacity_score * 100, 1),
                "qualified": not disqualifiers,
                "reasons": "\n".join(reason_lines),
                "disqualifiers": "；".join(disqualifiers),
                "matched_terms": matched_terms,
            }
        )

    qualified = sorted([r for r in results if r["qualified"]], key=lambda r: r["total_score"], reverse=True)
    excluded = sorted([r for r in results if not r["qualified"]], key=lambda r: r["total_score"], reverse=True)
    for rank, row in enumerate(qualified, start=1):
        row["rank"] = rank
    for row in excluded:
        row["rank"] = None
    return {
        "student": student,
        "weights": weights,
        "weight_labels": WEIGHT_LABELS,
        "qualified": qualified,
        "excluded": excluded,
        "summary": {
            "candidate_teachers": len(teachers),
            "qualified_count": len(qualified),
            "excluded_count": len(excluded),
        },
    }


def _candidate_text(candidate: CandidateProfile) -> str:
    return " ".join(
        str(x)
        for x in [candidate.research_direction, candidate.keywords, candidate.major, candidate.output_evidence]
        if x
    )


def _position_text(position: JobPosition) -> str:
    return " ".join(
        str(x)
        for x in [position.research_direction, position.research_topics, position.requirements_desc, position.discipline]
        if x
    )


def evaluate_position(db: Session, position: JobPosition) -> list[CandidateEvaluation]:
    weights = normalize_weights(
        json.loads(position.weights) if position.weights else None,
        DEFAULT_CANDIDATE_WEIGHTS,
        set(DEFAULT_CANDIDATE_WEIGHTS),
    )
    candidates = db.query(CandidateProfile).filter(CandidateProfile.position_id == position.id).all()
    position_text = _position_text(position)
    direction_scores = (
        tfidf_similarities(position_text, [_candidate_text(c) for c in candidates])
        if candidates else []
    )

    db.query(CandidateEvaluation).filter(CandidateEvaluation.position_id == position.id).delete()
    db.flush()

    evaluations = []
    for idx, candidate in enumerate(candidates):
        gaps = []
        hard_pass = True
        cand_rank = DEGREE_RANK.get(candidate.degree or "", 0)
        req_rank = DEGREE_RANK.get(position.required_degree or "", 0)
        if req_rank and cand_rank < req_rank:
            hard_pass = False
            gaps.append(f"学历不满足：要求{position.required_degree}，候选人学历为{candidate.degree or '未填写'}")
        if (candidate.outputs_count or 0) < (position.min_outputs or 0):
            hard_pass = False
            gaps.append(
                f"成果数量不满足：岗位最低要求 {position.min_outputs} 项，候选人记录 {candidate.outputs_count or 0} 项"
            )

        direction_score = direction_scores[idx] if idx < len(direction_scores) else 0.0
        denom_outputs = max((position.min_outputs or 0) * 2, 6)
        outputs_score = min(1.0, (candidate.outputs_count or 0) / denom_outputs)
        projects_score = min(1.0, (candidate.projects_count or 0) / 5)
        teaching_score = min(1.0, (candidate.teaching_years or 0) / 5)

        total = round(
            (
                direction_score * weights["direction"]
                + outputs_score * weights["outputs"]
                + projects_score * weights["projects"]
                + teaching_score * weights["teaching"]
            )
            * 100,
            1,
        )

        reason_lines = [
            f"研究方向相似度 {direction_score * 100:.1f}%（候选人方向/关键词 vs 岗位方向、主题与要求）",
            f"科研成果得分 {outputs_score * 100:.1f}%（档案记录 {candidate.outputs_count or 0} 项；岗位最低 {position.min_outputs or 0} 项）",
            f"项目经历得分 {projects_score * 100:.1f}%（档案记录 {candidate.projects_count or 0} 项）",
            f"教学经历得分 {teaching_score * 100:.1f}%（档案记录 {candidate.teaching_years or 0} 年）",
            f"权重：方向 {weights['direction'] * 100:.0f}% · 成果 {weights['outputs'] * 100:.0f}% · "
            f"项目 {weights['projects'] * 100:.0f}% · 教学 {weights['teaching'] * 100:.0f}%",
        ]
        if hard_pass:
            if direction_score < 0.3:
                gaps.append("研究方向与岗位方向文本相似度较低，建议人工核对研究方向。")
            if (candidate.unverified_fields or "").strip():
                gaps.append(f"待核验字段：{candidate.unverified_fields}")
        evidence_lines = [
            f"研究方向/关键词：{candidate.research_direction or '未填写'} / {candidate.keywords or '未填写'}",
            f"成果证据：{candidate.output_evidence or '未提供，记录数来自导入档案'}",
            f"项目证据：{candidate.project_evidence or '未提供'}",
            f"教学证据：{candidate.teaching_evidence or '未提供'}",
            f"资料来源：{candidate.source or '未标注'}"
            + (f"；待核验字段：{candidate.unverified_fields}" if candidate.unverified_fields else ""),
        ]

        evaluation = CandidateEvaluation(
            candidate_id=candidate.id,
            position_id=position.id,
            hard_pass=hard_pass,
            direction_score=round(direction_score * 100, 1),
            outputs_score=round(outputs_score * 100, 1),
            projects_score=round(projects_score * 100, 1),
            teaching_score=round(teaching_score * 100, 1),
            total_score=total,
            reasons="\n".join(reason_lines),
            gaps="；".join(gaps),
            evidence="\n".join(evidence_lines),
            review_status="pending",
        )
        db.add(evaluation)
        evaluations.append(evaluation)

    db.flush()
    ranked = sorted(
        [e for e in evaluations if e.hard_pass], key=lambda e: e.total_score, reverse=True
    )
    for rank, ev in enumerate(ranked, start=1):
        ev.rank = rank
    for ev in evaluations:
        if not ev.hard_pass:
            ev.rank = None
    db.commit()
    return (
        db.query(CandidateEvaluation)
        .filter(CandidateEvaluation.position_id == position.id)
        .order_by(CandidateEvaluation.hard_pass.desc(), CandidateEvaluation.total_score.desc())
        .all()
    )
