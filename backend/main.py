"""别纠结决策辅助 - FastAPI 应用入口。

启动流程：
  1. 初始化 SQLite（choice.db）
  2. 注册 6 个 API 路由
  3. 挂载前端静态资源（frontend/）
  4. 监听 8000 端口

启动方式：
    python main.py
    或 uvicorn main:app --reload --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 确保 backend/ 在 sys.path 中（用于 routes/services 的相对导入）
sys.path.insert(0, str(Path(__file__).parent))

from db import init_db  # noqa: E402
from routes import archive, chat, config_api, decision, modes, stats, tts  # noqa: E402

# 前端静态资源目录（choice-skill/frontend/）
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# 启动时初始化数据库
init_db()

app = FastAPI(
    title="别纠结决策辅助 API",
    description="辅助人做选择，不替代人做决定",
    version="0.8.4",
)

# ─── API 路由 ───────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(modes.router)
app.include_router(decision.router)
app.include_router(archive.router)
app.include_router(stats.router)
app.include_router(config_api.router)
app.include_router(tts.router)


# ─── 健康检查 ───────────────────────────────────────────────────


@app.get("/api/health")
def health() -> dict:
    """健康检查。"""
    return {"name": "别纠结 API", "status": "ok", "version": "0.8.3"}


# ─── 前端静态资源 ──────────────────────────────────────────────
# 仅当 frontend/ 目录存在时挂载（CLI-only 模式下不需要前端）
if FRONTEND_DIR.exists():
    styles_dir = FRONTEND_DIR / "styles"
    scripts_dir = FRONTEND_DIR / "scripts"
    assets_dir = FRONTEND_DIR / "assets"

    if styles_dir.exists():
        app.mount("/styles", StaticFiles(directory=str(styles_dir)), name="styles")
    if scripts_dir.exists():
        app.mount("/scripts", StaticFiles(directory=str(scripts_dir)), name="scripts")
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def serve_index() -> FileResponse:
        """根路径返回前端首页。"""
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """SPA fallback：非 API 路径返回 index.html。"""
        # 不拦截 /api/ 开头的路径
        if full_path.startswith("api/"):
            return FileResponse(str(FRONTEND_DIR / "index.html"), status_code=404)
        # 尝试返回静态文件
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        # fallback 到 index.html
        return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
