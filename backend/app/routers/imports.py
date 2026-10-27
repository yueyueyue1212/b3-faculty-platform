import csv
from io import StringIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ImportBatch, ImportRowError, User
from ..security import client_ip, get_current_user, require_editor
from ..services.audit import write_audit
from ..services.imports import (
    CANDIDATE_HEADERS,
    OUTPUT_HEADERS,
    TEACHER_HEADERS,
    _batch_result,
    csv_template,
    import_candidates,
    import_outputs,
    import_teachers,
    read_upload,
)

router = APIRouter(prefix="/api/imports", tags=["数据导入"])

TEMPLATES = {
    "teachers": (TEACHER_HEADERS, "教师档案导入模板.csv"),
    "research_outputs": (OUTPUT_HEADERS, "科研成果导入模板.csv"),
    "candidates": (CANDIDATE_HEADERS, "候选人档案导入模板.csv"),
}


@router.get("/templates/{kind}", summary="下载导入模板（CSV）")
def download_template(kind: str, user: User = Depends(get_current_user)):
    if kind not in TEMPLATES:
        raise HTTPException(status_code=404, detail="模板类型不存在")
    headers, filename = TEMPLATES[kind]
    return Response(
        content=csv_template(headers),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={kind}_template.csv; "
            f"filename*=UTF-8''{quote(filename)}"
        },
    )


@router.post("/teachers", summary="导入教师档案（Excel/CSV）")
async def upload_teachers(file: UploadFile = File(...), request: Request = None,
                          user: User = Depends(require_editor), db: Session = Depends(get_db)):
    df = await read_upload(file)
    result = import_teachers(db, df, file.filename or "teachers.csv", user.username)
    write_audit(db, user, "import", "teacher", result["id"],
                f"导入教师档案：成功 {result['success_rows']}，失败 {result['failed_rows']}，"
                f"重复 {result['duplicate_rows']}", client_ip(request))
    return result


@router.post("/research-outputs", summary="导入科研成果（Excel/CSV）")
async def upload_outputs(file: UploadFile = File(...), request: Request = None,
                         user: User = Depends(require_editor), db: Session = Depends(get_db)):
    df = await read_upload(file)
    result = import_outputs(db, df, file.filename or "outputs.csv", user.username)
    write_audit(db, user, "import", "research_output", result["id"],
                f"导入科研成果：成功 {result['success_rows']}，失败 {result['failed_rows']}，"
                f"重复 {result['duplicate_rows']}", client_ip(request))
    return result


@router.post("/candidates", summary="导入候选人档案（Excel/CSV）")
async def upload_candidates(position_id: int = Query(...), file: UploadFile = File(...),
                            request: Request = None,
                            user: User = Depends(require_editor), db: Session = Depends(get_db)):
    df = await read_upload(file)
    result = import_candidates(
        db, df, file.filename or "candidates.csv", user.username, position_id
    )
    write_audit(db, user, "import", "candidate_profile", result["id"],
                f"导入候选人：成功 {result['success_rows']}，失败 {result['failed_rows']}",
                client_ip(request))
    return result


@router.get("/batches", summary="导入批次列表")
def list_batches(
    import_type: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ImportBatch)
    if import_type:
        query = query.filter(ImportBatch.import_type == import_type)
    if status:
        query = query.filter(ImportBatch.status == status)
    total = query.count()
    rows = (query.order_by(ImportBatch.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    items = []
    for row in rows:
        item = _batch_result(row, "")
        item.pop("message", None)
        item["error_count"] = db.query(ImportRowError).filter(
            ImportRowError.batch_id == row.id
        ).count()
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/batches/{batch_id}/errors", summary="导入错误明细")
def batch_errors(
    batch_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    query = db.query(ImportRowError).filter(ImportRowError.batch_id == batch_id)
    total = query.count()
    rows = (query.order_by(ImportRowError.row_number, ImportRowError.id)
            .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "batch": _batch_result(batch, ""),
        "items": [
            {
                "id": r.id,
                "row_number": r.row_number,
                "column_name": r.column_name,
                "error_message": r.error_message,
                "raw_value": r.raw_value,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/batches/{batch_id}/errors/export", summary="下载导入错误明细（CSV）")
def export_errors(batch_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="导入批次不存在")
    rows = (db.query(ImportRowError).filter(ImportRowError.batch_id == batch_id)
            .order_by(ImportRowError.row_number, ImportRowError.id).all())
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["行号", "字段", "错误原因", "原始值"])
    for row in rows:
        writer.writerow([row.row_number, row.column_name, row.error_message, row.raw_value or ""])
    content = ("﻿" + buffer.getvalue()).encode("utf-8")
    filename = f"import_errors_{batch_id}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}; "
            f"filename*=UTF-8''{quote('导入错误明细.csv')}"
        },
    )
