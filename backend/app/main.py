import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import APP_VERSION, AUTO_SEED_ON_STARTUP, BUNDLE_DIR, CORS_ORIGINS
from .database import Base, SessionLocal, engine
from .logging_setup import configure_logging
from .routers import admin, advisor, analytics, auth, imports, outputs, projects, promotion, recruitment, records, teachers
from .seed import seed_all

configure_logging()
logger = logging.getLogger("b3")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if AUTO_SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            result = seed_all(db, force=False)
            if result.get("skipped"):
                logger.info("Demo data already present: %s teachers", result.get("teachers"))
            else:
                logger.info("Demo data initialized: %s", result)
        except Exception as exc:  # never prevent the API from starting
            logger.exception("Demo data initialization failed: %s", exc)
        finally:
            db.close()
    yield


app = FastAPI(
    title="高校师资/人才智能画像与辅助管理平台（B3）",
    description=(
        "教师多维画像、人才结构分析、导师智能匹配、职称申报材料归集、"
        "青年人才引进辅助评估与数据管理平台。\n\n"
        "所有演示数据均以“模拟数据（B3演示）”标记，不代表真实高校数据。"
        "AI 能力可选，未配置 API Key 时规则算法与全部 CRUD 仍可使用。"
    ),
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        location = ".".join(str(x) for x in error.get("loc", []) if x not in ("body", "query"))
        details.append(f"{location or '参数'}: {error.get('msg')}")
    return JSONResponse(
        status_code=422,
        content={"detail": "参数校验失败：" + "；".join(details), "errors": details},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误：{type(exc).__name__}，请查看后端日志或联系管理员"},
    )


@app.get("/api/health", tags=["系统"], summary="健康检查")
def health():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": "B3 高校师资人才智能画像平台",
        "version": APP_VERSION,
        "database": db_status,
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.get("/health", include_in_schema=False)
def health_alias():
    return health()


app.include_router(auth.router)
app.include_router(teachers.router)
app.include_router(outputs.router)
app.include_router(projects.router)
app.include_router(records.teaching_router)
app.include_router(records.service_router)
app.include_router(analytics.router)
app.include_router(advisor.students_router)
app.include_router(advisor.router)
app.include_router(promotion.router)
app.include_router(recruitment.router)
app.include_router(imports.router)
app.include_router(admin.router)


@app.api_route(
    "/api/{unknown_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
def unknown_api(unknown_path: str):
    """Keep unknown API paths as JSON 404s instead of the SPA history fallback."""
    raise HTTPException(status_code=404, detail=f"接口不存在：/api/{unknown_path}")


# Optionally serve the built frontend from the same origin (single-server demo).
class SPAStaticFiles(StaticFiles):
    """Serve built assets and fall back to index.html for Vue history routes."""

    @staticmethod
    def _is_reserved(path: str) -> bool:
        return path.lstrip("/").startswith(("api/", "health"))

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or self._is_reserved(path):
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404 and not self._is_reserved(path):
            return await super().get_response("index.html", scope)
        return response


_dist = BUNDLE_DIR / "frontend" / "dist"
if _dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(_dist), html=True), name="frontend")
