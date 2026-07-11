from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    account_id: str = Field(default="demo-account", min_length=1, max_length=128)
    region: str = Field(default="us", min_length=1, max_length=32)
    commit: bool = Field(default=False)


class SyncTelemetry(BaseModel):
    account_id: str
    region: str
    source: str = Field(default="psn")
    fetched_at: str
    correlation_id: str
    trophies_total: int
    trophies_earned: int
    completion: int
    recently_played: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class JudyProposal(BaseModel):
    transaction_metadata: dict[str, str]
    proposed_action: dict[str, Any]
    agent_rationale: str
    sync_telemetry: SyncTelemetry
