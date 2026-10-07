"""RestoPilot FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import confirmations, dashboard, sales, whatsapp
from app.core.config import get_settings
from app.db import seed
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if get_settings().mock_mode:
        seed.ensure_demo_data()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["whatsapp"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(
        confirmations.router, prefix="/api/confirmations", tags=["confirmations"]
    )
    app.include_router(sales.router, prefix="/api/sales", tags=["sales"])

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
