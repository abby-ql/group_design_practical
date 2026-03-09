from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.risk import router as risk_router
from app.api.trends import router as trends_router
from app.api.alerts import router as alerts_router
from app.core.db import init_db

app = FastAPI(
    title="Trend-aware Risk Signals Engine (Demo)",
    version="0.1.0",
    description="Student demonstrator: transparent risk indicators + UK trend overlap alerts."
)

@app.on_event("startup")
def _startup() -> None:
    init_db()

app.include_router(risk_router, prefix="/risk", tags=["risk"])
app.include_router(trends_router, prefix="/trends", tags=["trends"])
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])

# Serve the tiny demo UI (static)
app.mount("/static", StaticFiles(directory="web", html=True), name="static")

@app.get("/", include_in_schema=False)
def index():
    return FileResponse("web/index.html")

@app.get("/health", tags=["meta"])
def health():
    return {"ok": True}
