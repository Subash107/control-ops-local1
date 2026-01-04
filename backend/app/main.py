from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select

from .core.config import settings
from .database import SessionLocal
from .models import User, Tool
from .security import hash_password
from .routers.auth import router as auth_router
from .routers.tools import router as tools_router
from .routers.admin import router as admin_router


def _seed_default_admin(db: Session) -> None:
    existing = db.scalar(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
    if existing:
        return
    admin = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    db.commit()


def _seed_sample_tools(db: Session) -> None:
    if db.scalar(select(Tool).limit(1)) is not None:
        return
    db.add_all(
        [
            Tool(name="Jenkins", description="CI/CD automation server", url="https://www.jenkins.io/", category="ci-cd", tags=["cicd", "pipelines"]),
            Tool(name="Prometheus", description="Monitoring and alerting toolkit", url="https://prometheus.io/", category="observability", tags=["metrics", "monitoring"]),
            Tool(name="Grafana", description="Visualization and dashboards", url="https://grafana.com/", category="observability", tags=["dashboards", "visualization"]),
        ]
    )
    db.commit()


def create_app() -> FastAPI:
    app = FastAPI(title="DevOps Control Plane", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(tools_router)
    app.include_router(admin_router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


app = create_app()


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        _seed_default_admin(db)
        _seed_sample_tools(db)
    finally:
        db.close()
