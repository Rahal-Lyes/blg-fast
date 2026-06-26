import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routes import auth, users, reports, notifications, admin,stats

app = FastAPI(
    title="Balligh+ API",
    description="Backend API for the Smart Neighborhood Issue Reporting Platform — منصة الإبلاغ الذكي عن مشاكل الأحياء",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded images) ───────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api")
app.include_router(users.router,         prefix="/api")
app.include_router(reports.router,       prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(admin.router,         prefix="/api")
app.include_router(stats.router, prefix="/api")

@app.get("/debug/uploads")
def debug_uploads():
    import os
    return {
        "files": os.listdir(settings.UPLOAD_DIR),
        "path": settings.UPLOAD_DIR
    }
@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "app": "Balligh+ API", "version": "1.0.0"}
