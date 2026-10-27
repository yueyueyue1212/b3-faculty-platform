from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import get_current_user
from ..services.analytics import (
    build_report_workbook,
    dashboard,
    data_quality,
    get_options,
    get_teachers,
    talent_review,
)

router = APIRouter(prefix="/api/analytics", tags=["统计分析与人才盘点"])


@router.get("/filters", summary="统计筛选选项")
def filters(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_options(db)


@router.get("/dashboard", summary="人才驾驶舱统计")
def dashboard_api(
    college: str | None = None,
    discipline: str | None = None,
    title: str | None = None,
    status: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dashboard(db, college, discipline, title, year_from, year_to, status)


@router.get("/data-quality", summary="数据质量检查")
def data_quality_api(
    college: str | None = None,
    discipline: str | None = None,
    title: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    teachers = get_teachers(db, college, discipline, title)
    return data_quality(db, teachers)


@router.get("/talent-review", summary="人才盘点报告数据")
def talent_review_api(
    college: str | None = None,
    discipline: str | None = None,
    title: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return talent_review(db, college, discipline, title, year_from, year_to)


@router.get("/talent-review/export", summary="导出人才盘点报告（Excel）")
def talent_review_export(
    college: str | None = None,
    discipline: str | None = None,
    title: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = talent_review(db, college, discipline, title, year_from, year_to)
    label_parts = [
        f"学院={college}" if college else "",
        f"学科={discipline}" if discipline else "",
        f"职称={title}" if title else "",
        f"年份={year_from or ''}-{year_to or ''}" if (year_from or year_to) else "",
    ]
    label = "；".join([p for p in label_parts if p]) or "全部教师"
    stream = build_report_workbook(review, label)
    filename = "talent_review_report.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}; "
            f"filename*=UTF-8''{quote('人才盘点报告.xlsx')}"
        },
    )
