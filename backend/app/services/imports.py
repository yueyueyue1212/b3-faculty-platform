"""Excel/CSV import with row-level validation and error reporting."""
import re
from io import BytesIO

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import ALLOWED_UPLOAD_SUFFIXES, MAX_UPLOAD_BYTES
from ..models import ImportBatch, ImportRowError, ResearchOutput, Teacher
from ..schemas import DEGREES, OUTPUT_TYPES, TEACHER_STATUSES, TITLES
from ..utils import parse_date

TEACHER_HEADERS = [
    "teacher_no", "name", "college", "discipline", "title", "department", "degree",
    "position", "hire_date", "gender", "birth_year", "research_direction", "bio",
    "skills", "research_keywords", "status", "advisor_qualified", "enrollment_status",
    "capacity", "current_students", "phone", "email", "data_source",
]
TEACHER_REQUIRED = ["teacher_no", "name", "college", "discipline", "title"]

OUTPUT_HEADERS = [
    "teacher_no", "output_type", "title", "venue", "publish_date", "level", "authors", "doi",
]
OUTPUT_REQUIRED = ["teacher_no", "output_type", "title"]
CANDIDATE_HEADERS = [
    "name", "degree", "graduate_school", "major", "research_direction", "keywords",
    "outputs_count", "projects_count", "teaching_years", "output_evidence",
    "project_evidence", "teaching_evidence", "source", "unverified_fields",
]
CANDIDATE_REQUIRED = ["name", "degree", "major", "research_direction"]
OUTPUT_TYPE_ALIASES = {
    "论文": "paper", "paper": "paper", "专利": "patent", "patent": "patent",
    "著作": "book", "book": "book", "报告": "report", "report": "report",
}
ENROLLMENT_ALIASES = {
    "开放": "open", "open": "open", "已满": "full", "full": "full",
    "未开放": "closed", "closed": "closed",
}
BOOL_TRUE = {"是", "true", "1", "yes", "y", "有"}
BOOL_FALSE = {"否", "false", "0", "no", "n", "无"}


def _clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def _as_int(value, field, errors):
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        errors.append((field, f"{field} 必须是整数，当前值：{value}", value))
        return None


def _as_float(value, field, errors):
    value = _clean(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append((field, f"{field} 必须是数字，当前值：{value}", value))
        return None


async def read_upload(file: UploadFile) -> pd.DataFrame:
    filename = file.filename or "upload"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 .csv 或 .xlsx 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 {MAX_UPLOAD_BYTES // 1024 // 1024} MB）",
        )
    try:
        if suffix == ".csv":
            df = None
            last_error = None
            for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
                try:
                    df = pd.read_csv(BytesIO(content), encoding=encoding)
                    break
                except UnicodeDecodeError as exc:
                    last_error = exc
            if df is None:
                raise ValueError(f"无法识别 CSV 编码：{last_error}")
        else:
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败：{exc}")
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise HTTPException(status_code=400, detail="文件中没有数据行")
    if len(df) > 5000:
        raise HTTPException(status_code=400, detail="单次导入不能超过 5000 行")
    return df


def _create_batch(db: Session, filename: str, import_type: str, user: str,
                  total: int = 0, status: str = "completed") -> ImportBatch:
    batch = ImportBatch(
        filename=filename, import_type=import_type, total_rows=total,
        status=status, created_by=user,
    )
    db.add(batch)
    db.flush()
    return batch


def _add_error(db: Session, batch: ImportBatch, row_number: int, column: str,
               message: str, raw=None):
    db.add(ImportRowError(
        batch_id=batch.id, row_number=row_number, column_name=column,
        error_message=message[:400], raw_value=str(raw)[:300] if raw is not None else None,
    ))


def import_teachers(db: Session, df: pd.DataFrame, filename: str, username: str) -> dict:
    batch = _create_batch(db, filename, "teachers", username, total=len(df))
    missing_cols = [c for c in TEACHER_REQUIRED if c not in df.columns]
    if missing_cols:
        batch.status = "failed"
        _add_error(db, batch, 0, "columns", f"缺少必需列：{', '.join(missing_cols)}")
        db.commit()
        return _batch_result(batch, "缺少必需列，未导入任何记录")

    existing_nos = {r[0] for r in db.query(Teacher.teacher_no).all()}
    file_nos = set()
    success = failed = duplicate = 0

    for idx, row in df.iterrows():
        row_number = int(idx) + 2
        errors = []
        data = {col: _clean(row.get(col)) for col in TEACHER_HEADERS if col in df.columns}

        for col in TEACHER_REQUIRED:
            if not data.get(col):
                errors.append((col, "必填字段为空", ""))
        teacher_no = data.get("teacher_no")
        if teacher_no:
            if teacher_no in existing_nos:
                errors.append(("teacher_no", "教师编号已存在于系统（重复记录）", teacher_no))
            if teacher_no in file_nos:
                errors.append(("teacher_no", "教师编号在本次文件中重复", teacher_no))
        if data.get("title") and data["title"] not in TITLES:
            errors.append(("title", f"职称不合法，应为：{'/'.join(TITLES)}", data["title"]))
        if data.get("degree") and data["degree"] not in DEGREES:
            errors.append(("degree", f"学历不合法，应为：{'/'.join(DEGREES)}", data["degree"]))
        if data.get("status") and data["status"] not in TEACHER_STATUSES:
            errors.append(("status", "教师状态不合法（active/on_leave/retired）", data["status"]))
        email = data.get("email")
        if email and (not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)):
            errors.append(("email", "邮箱格式不正确", email))

        hire_date = None
        hire_raw = data.get("hire_date")
        if hire_raw:
            hire_date = parse_date(hire_raw)
            if not hire_date:
                errors.append(("hire_date", "入职日期格式不正确（建议 YYYY-MM-DD）", hire_raw))

        birth_year = _as_int(data.get("birth_year"), "birth_year", errors) if data.get("birth_year") else None
        if birth_year and not (1900 <= birth_year <= 2010):
            errors.append(("birth_year", "出生年份应在 1900-2010 之间", birth_year))

        capacity = _as_int(data.get("capacity"), "capacity", errors) if data.get("capacity") else 0
        current_students = _as_int(
            data.get("current_students"), "current_students", errors
        ) if data.get("current_students") else 0
        if capacity is not None and capacity < 0:
            errors.append(("capacity", "指导容量不能为负数", capacity))
        if current_students is not None and current_students < 0:
            errors.append(("current_students", "在读人数不能为负数", current_students))

        advisor_raw = data.get("advisor_qualified")
        advisor_qualified = False
        if advisor_raw:
            lowered = advisor_raw.lower()
            if lowered in BOOL_TRUE:
                advisor_qualified = True
            elif lowered not in BOOL_FALSE:
                errors.append(("advisor_qualified", "导师资格应为 是/否", advisor_raw))
        enrollment = data.get("enrollment_status")
        if enrollment:
            enrollment = ENROLLMENT_ALIASES.get(enrollment.lower(), enrollment)
            if enrollment not in ("open", "full", "closed"):
                errors.append(("enrollment_status", "招生状态应为 open/full/closed", enrollment))

        if errors:
            already_counted = any(e[0] == "teacher_no" and "已存在" in e[1] for e in errors) or \
                any(e[0] == "teacher_no" and "文件中重复" in e[1] for e in errors)
            if already_counted:
                duplicate += 1
            else:
                failed += 1
            for col, msg, raw in errors:
                _add_error(db, batch, row_number, col, msg, raw)
            continue

        file_nos.add(teacher_no)
        teacher = Teacher(
            teacher_no=teacher_no,
            name=data.get("name"),
            college=data.get("college"),
            discipline=data.get("discipline"),
            title=data.get("title"),
            department=data.get("department"),
            degree=data.get("degree"),
            position=data.get("position"),
            hire_date=hire_date,
            gender=data.get("gender"),
            birth_year=birth_year,
            research_direction=data.get("research_direction"),
            bio=data.get("bio"),
            skills=data.get("skills"),
            research_keywords=data.get("research_keywords"),
            status=data.get("status") or "active",
            advisor_qualified=advisor_qualified,
            enrollment_status=enrollment or "closed",
            capacity=capacity or 0,
            current_students=current_students or 0,
            phone=data.get("phone"),
            email=data.get("email"),
            data_source=data.get("data_source") or f"导入:{filename}",
            verification_status="pending",
        )
        db.add(teacher)
        success += 1

    batch.success_rows = success
    batch.failed_rows = failed
    batch.duplicate_rows = duplicate
    db.commit()
    message = f"导入完成：成功 {success} 行，失败 {failed} 行，重复 {duplicate} 行"
    return _batch_result(batch, message)


def import_outputs(db: Session, df: pd.DataFrame, filename: str, username: str) -> dict:
    batch = _create_batch(db, filename, "research_outputs", username, total=len(df))
    missing_cols = [c for c in OUTPUT_REQUIRED if c not in df.columns]
    if missing_cols:
        batch.status = "failed"
        _add_error(db, batch, 0, "columns", f"缺少必需列：{', '.join(missing_cols)}")
        db.commit()
        return _batch_result(batch, "缺少必需列，未导入任何记录")

    teachers = {t.teacher_no: t for t in db.query(Teacher).all()}
    existing = set()
    for row in db.query(ResearchOutput).all():
        year = row.publish_date.year if row.publish_date else None
        existing.add((row.teacher_id, re.sub(r"\s+", "", row.title.lower()), year))
    file_keys = set()
    success = failed = duplicate = 0

    for idx, row in df.iterrows():
        row_number = int(idx) + 2
        errors = []
        teacher_no = _clean(row.get("teacher_no"))
        raw_type = _clean(row.get("output_type"))
        title = _clean(row.get("title"))
        output_type = OUTPUT_TYPE_ALIASES.get((raw_type or "").lower(), raw_type)

        if not teacher_no:
            errors.append(("teacher_no", "教师编号为空", ""))
        elif teacher_no not in teachers:
            errors.append(("teacher_no", "教师编号在系统中不存在", teacher_no))
        if not raw_type:
            errors.append(("output_type", "成果类型为空", ""))
        elif output_type not in OUTPUT_TYPES:
            errors.append(("output_type", "成果类型应为 论文/专利/著作/报告（或 paper/patent/book/report）", raw_type))
        if not title:
            errors.append(("title", "成果名称为空", ""))

        publish_raw = _clean(row.get("publish_date"))
        publish_date = parse_date(publish_raw) if publish_raw else None
        if publish_raw and not publish_date:
            errors.append(("publish_date", "日期格式不正确（建议 YYYY-MM-DD）", publish_raw))

        key = None
        teacher = teachers.get(teacher_no) if teacher_no else None
        if teacher and title:
            key = (teacher.id, re.sub(r"\s+", "", title.lower()), publish_date.year if publish_date else None)
            if key in existing or key in file_keys:
                errors.append(("title", "重复成果（同一教师、同名成果、同年份）", title))

        if errors:
            if any("重复成果" in e[1] for e in errors):
                duplicate += 1
            else:
                failed += 1
            for col, msg, raw in errors:
                _add_error(db, batch, row_number, col, msg, raw)
            continue

        file_keys.add(key)
        db.add(ResearchOutput(
            teacher_id=teacher.id,
            output_type=output_type,
            title=title,
            venue=_clean(row.get("venue")),
            publish_date=publish_date,
            level=_clean(row.get("level")),
            authors=_clean(row.get("authors")),
            doi=_clean(row.get("doi")),
            data_source=_clean(row.get("data_source")) or f"导入:{filename}",
        ))
        success += 1

    batch.success_rows = success
    batch.failed_rows = failed
    batch.duplicate_rows = duplicate
    db.commit()
    message = f"导入完成：成功 {success} 行，失败 {failed} 行，重复 {duplicate} 行"
    return _batch_result(batch, message)


def import_candidates(db: Session, df: pd.DataFrame, filename: str, username: str,
                      position_id: int) -> dict:
    from ..models import CandidateProfile, JobPosition

    batch = _create_batch(db, filename, "candidates", username, total=len(df))
    position = db.get(JobPosition, position_id)
    if not position:
        batch.status = "failed"
        _add_error(db, batch, 0, "position_id", "关联岗位不存在")
        db.commit()
        return _batch_result(batch, "关联岗位不存在，未导入任何记录")
    missing_cols = [c for c in CANDIDATE_REQUIRED if c not in df.columns]
    if missing_cols:
        batch.status = "failed"
        _add_error(db, batch, 0, "columns", f"缺少必需列：{', '.join(missing_cols)}")
        db.commit()
        return _batch_result(batch, "缺少必需列，未导入任何记录")

    existing_names = {
        r[0] for r in db.query(CandidateProfile.name)
        .filter(CandidateProfile.position_id == position_id).all()
    }
    file_names = set()
    success = failed = duplicate = 0

    for idx, row in df.iterrows():
        row_number = int(idx) + 2
        errors = []
        data = {col: _clean(row.get(col)) for col in CANDIDATE_HEADERS if col in df.columns}
        for col in CANDIDATE_REQUIRED:
            if not data.get(col):
                errors.append((col, "必填字段为空", ""))
        name = data.get("name")
        if name:
            if name in existing_names:
                errors.append(("name", "该岗位下已存在同名候选人（疑似重复）", name))
            if name in file_names:
                errors.append(("name", "候选人在本次文件中重复", name))
        if data.get("degree") and data["degree"] not in DEGREES:
            errors.append(("degree", f"学历不合法，应为：{'/'.join(DEGREES)}", data["degree"]))
        outputs_count = _as_int(data.get("outputs_count"), "outputs_count", errors) or 0
        projects_count = _as_int(data.get("projects_count"), "projects_count", errors) or 0
        teaching_years = _as_float(data.get("teaching_years"), "teaching_years", errors) or 0
        if outputs_count < 0:
            errors.append(("outputs_count", "成果数量不能为负数", outputs_count))
        if projects_count < 0:
            errors.append(("projects_count", "项目数量不能为负数", projects_count))
        if teaching_years < 0:
            errors.append(("teaching_years", "教学年限不能为负数", teaching_years))

        if errors:
            if any("重复" in e[1] for e in errors):
                duplicate += 1
            else:
                failed += 1
            for col, msg, raw in errors:
                _add_error(db, batch, row_number, col, msg, raw)
            continue

        file_names.add(name)
        db.add(CandidateProfile(
            name=name,
            position_id=position_id,
            degree=data.get("degree"),
            graduate_school=data.get("graduate_school"),
            major=data.get("major"),
            research_direction=data.get("research_direction"),
            keywords=data.get("keywords"),
            outputs_count=outputs_count,
            projects_count=projects_count,
            teaching_years=teaching_years,
            output_evidence=data.get("output_evidence"),
            project_evidence=data.get("project_evidence"),
            teaching_evidence=data.get("teaching_evidence"),
            source=data.get("source") or f"导入:{filename}",
            unverified_fields=data.get("unverified_fields"),
        ))
        success += 1

    batch.success_rows = success
    batch.failed_rows = failed
    batch.duplicate_rows = duplicate
    db.commit()
    return _batch_result(
        batch, f"导入完成：成功 {success} 行，失败 {failed} 行，重复 {duplicate} 行"
    )


def _batch_result(batch: ImportBatch, message: str) -> dict:
    return {
        "id": batch.id,
        "filename": batch.filename,
        "import_type": batch.import_type,
        "total_rows": batch.total_rows,
        "success_rows": batch.success_rows,
        "failed_rows": batch.failed_rows,
        "duplicate_rows": batch.duplicate_rows,
        "status": batch.status,
        "created_by": batch.created_by,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "message": message,
    }


def csv_template(headers: list[str]) -> bytes:
    return ("﻿" + ",".join(headers) + "\r\n").encode("utf-8")
