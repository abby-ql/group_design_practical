from __future__ import annotations

from typing import Optional, Any, Dict, List
from datetime import datetime

from sqlmodel import SQLModel, Field, Column, JSON


class Item(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str
    platform: str
    visibility: str
    language: str = "en"
    created_at: datetime
    text: str
    edge_case: Optional[str] = None
    item_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class RiskScore(SQLModel, table=True):
    id: str = Field(primary_key=True)
    item_id: str = Field(index=True, foreign_key="item.id")
    computed_at: datetime
    total_score: float
    bucket: str
    reasons: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    decomposition: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))


class TrendTopic(SQLModel, table=True):
    term: str = Field(primary_key=True)
    volume: int
    tone: float
    last_seen: datetime
    source: str


class Alert(SQLModel, table=True):
    id: str = Field(primary_key=True)
    created_at: datetime
    item_id: str = Field(index=True, foreign_key="item.id")
    trend_term: str = Field(index=True, foreign_key="trendtopic.term")
    old_bucket: Optional[str] = None
    new_bucket: Optional[str] = None
    risk_delta: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


# --- API schemas (non-table) ---

class ItemIn(SQLModel):
    text: str
    created_at: datetime
    item_metadata: Dict[str, Any] = {}
    platform: Optional[str] = None
    visibility: Optional[str] = None
    language: Optional[str] = "en"


class RiskScoreOut(SQLModel):
    total_score: float
    bucket: str
    reasons: List[Dict[str, Any]]
    decomposition: List[Dict[str, Any]]


class TrendTopicOut(SQLModel):
    term: str
    volume: int
    tone: float
    last_seen: datetime
    source: str
