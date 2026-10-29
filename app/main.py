import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.brand import APP_NAME
from app.core.paths import ENV_PATH, STATIC, WORKSPACE
from app.api.routes.assets import router as assets_router
from app.api.routes.auto_pipeline import router as auto_pipeline_router
from app.api.routes.generation import router as generation_router
from app.api.routes.jianying import router as jianying_router
from app.api.routes.project import router as project_router
from app.api.routes.prompts import router as prompts_router
from app.api.routes.render import router as render_router
from app.api.routes.templates import router as templates_router


try:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)
except Exception:
    pass


app = FastAPI(title=APP_NAME, version="0.1.0")

logger = logging.getLogger("video-workbench")


@app.exception_handler(HTTPException)
async def log_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    # 把接口错误写进容器日志，方便排查“生成失败”的具体原因。
    # 错误信息里只包含 host/path，不会包含 API Key。
    logger.warning("%s %s -> %s: %s", request.method, request.url.path, exc.status_code, exc.detail)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.middleware("http")
async def log_slow_api_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    if request.url.path.startswith("/api/") and elapsed >= 1.0:
        logger.warning("%s %s -> %s 耗时 %.2fs", request.method, request.url.path, response.status_code, elapsed)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)
app.include_router(prompts_router)
app.include_router(templates_router)
app.include_router(assets_router)
app.include_router(auto_pipeline_router)
app.include_router(generation_router)
app.include_router(render_router)
app.include_router(jianying_router)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"ok": "true"}


app.mount("/static", StaticFiles(directory=STATIC), name="static")
WORKSPACE.mkdir(parents=True, exist_ok=True)
app.mount("/workspace", StaticFiles(directory=WORKSPACE), name="workspace")
