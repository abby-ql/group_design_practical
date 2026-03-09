from __future__ import annotations

import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reputation_demo.db")

# SQLite needs this connect arg
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db() -> None:
    # Import models so SQLModel metadata is populated
    from app.core.models import Item, RiskScore, TrendTopic, Alert  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)
