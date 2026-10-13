"""
Hospital Operations Intelligence System — FastAPI application entry point.

Wires the analytics, ML, agent and meta routers, enables CORS for the React
frontend, and bootstraps the warehouse on first run if it is missing.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import db_exists
from app.api import analytics, ml, agent, meta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="BI + ML + AI-Agent platform for hospital operations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(ml.router, prefix=settings.api_prefix)
app.include_router(agent.router, prefix=settings.api_prefix)
app.include_router(meta.router, prefix=settings.api_prefix)


@app.on_event("startup")
def _bootstrap():
    if not db_exists():
        logger.info("Warehouse missing — building it now...")
        from app.etl.build_warehouse import build_warehouse
        build_warehouse()
        logger.info("Warehouse built.")


@app.get("/")
def root():
    return {"app": settings.app_name, "status": "ok", "docs": "/docs", "api": settings.api_prefix}


@app.get(f"{settings.api_prefix}/health")
def health():
    return {"status": "ok", "warehouse": db_exists()}
