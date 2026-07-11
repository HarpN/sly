from __future__ import annotations

import json
import sqlite3

from app.config import settings
from app.keeper_export import export_telemetry
from app.models import SyncTelemetry


def _snapshot_map(db_path: str, entity_key: str) -> dict[str, dict]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT version_label, payload_json
            FROM keeper_snapshots
            WHERE entity_type = 'game' AND entity_key = ?
            """,
            (entity_key,),
        ).fetchall()
    return {str(row["version_label"]): json.loads(str(row["payload_json"])) for row in rows}


def test_snapshot_promotion_for_game_exports(tmp_path, monkeypatch) -> None:
    keeper_db = tmp_path / "keeper_sly.db"
    monkeypatch.setattr(settings, "keeper_export_enabled", True)
    monkeypatch.setattr(settings, "keeper_db_path", str(keeper_db))
    monkeypatch.setattr(settings, "psn_platform", "PS5")

    export_telemetry(
        SyncTelemetry(
            account_id="acct",
            region="us",
            fetched_at="2026-07-11T00:00:00+00:00",
            correlation_id="sync-a",
            trophies_total=100,
            trophies_earned=50,
            completion=50,
            recently_played=["Astro Bot"],
        )
    )

    snapshots = _snapshot_map(str(keeper_db), "Astro Bot::PS5")
    assert set(snapshots.keys()) == {"LATEST"}
    assert snapshots["LATEST"]["correlation_id"] == "sync-a"

    export_telemetry(
        SyncTelemetry(
            account_id="acct",
            region="us",
            fetched_at="2026-07-11T00:05:00+00:00",
            correlation_id="sync-b",
            trophies_total=120,
            trophies_earned=84,
            completion=70,
            recently_played=["Astro Bot"],
        )
    )

    snapshots = _snapshot_map(str(keeper_db), "Astro Bot::PS5")
    assert set(snapshots.keys()) == {"LATEST", "PREVIOUS", "STABLE"}
    assert snapshots["LATEST"]["correlation_id"] == "sync-b"
    assert snapshots["PREVIOUS"]["correlation_id"] == "sync-a"
    assert snapshots["STABLE"]["correlation_id"] == "sync-a"

    export_telemetry(
        SyncTelemetry(
            account_id="acct",
            region="us",
            fetched_at="2026-07-11T00:10:00+00:00",
            correlation_id="sync-c",
            trophies_total=140,
            trophies_earned=112,
            completion=80,
            recently_played=["Astro Bot"],
        )
    )

    snapshots = _snapshot_map(str(keeper_db), "Astro Bot::PS5")
    assert snapshots["LATEST"]["correlation_id"] == "sync-c"
    assert snapshots["PREVIOUS"]["correlation_id"] == "sync-b"
    assert snapshots["STABLE"]["correlation_id"] == "sync-a"
