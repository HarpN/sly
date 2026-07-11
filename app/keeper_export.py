from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import settings
from .models import SyncTelemetry


def _ensure_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS keeper_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_agent TEXT NOT NULL,
            game_title TEXT NOT NULL,
            platform TEXT NOT NULL,
            completion_rate REAL NOT NULL DEFAULT 0,
            trophy_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(game_title, platform)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS keeper_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_key TEXT NOT NULL,
            version_label TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (version_label IN ('LATEST', 'PREVIOUS', 'STABLE')),
            UNIQUE(entity_type, entity_key, version_label)
        )
        """
    )


def _promote_snapshots(
    connection: sqlite3.Connection,
    *,
    entity_type: str,
    entity_key: str,
    latest_payload_json: str,
    created_at: str,
) -> None:
    current_latest = connection.execute(
        """
        SELECT payload_json, created_at
        FROM keeper_snapshots
        WHERE entity_type = ? AND entity_key = ? AND version_label = 'LATEST'
        """,
        (entity_type, entity_key),
    ).fetchone()

    if current_latest is not None and str(current_latest["payload_json"]) != latest_payload_json:
        connection.execute(
            """
            INSERT OR REPLACE INTO keeper_snapshots (
                entity_type, entity_key, version_label, payload_json, created_at
            ) VALUES (?, ?, 'PREVIOUS', ?, ?)
            """,
            (entity_type, entity_key, str(current_latest["payload_json"]), str(current_latest["created_at"])),
        )

        has_stable = connection.execute(
            """
            SELECT 1
            FROM keeper_snapshots
            WHERE entity_type = ? AND entity_key = ? AND version_label = 'STABLE'
            """,
            (entity_type, entity_key),
        ).fetchone()
        if has_stable is None:
            connection.execute(
                """
                INSERT OR REPLACE INTO keeper_snapshots (
                    entity_type, entity_key, version_label, payload_json, created_at
                ) VALUES (?, ?, 'STABLE', ?, ?)
                """,
                (entity_type, entity_key, str(current_latest["payload_json"]), str(current_latest["created_at"])),
            )

    connection.execute(
        """
        INSERT OR REPLACE INTO keeper_snapshots (
            entity_type, entity_key, version_label, payload_json, created_at
        ) VALUES (?, ?, 'LATEST', ?, ?)
        """,
        (entity_type, entity_key, latest_payload_json, created_at),
    )


def export_telemetry(telemetry: SyncTelemetry) -> None:
    if not settings.keeper_export_enabled:
        return

    db_path = Path(settings.keeper_db_path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path, check_same_thread=False) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_tables(connection)

        for game_title in telemetry.recently_played:
            connection.execute(
                """
                INSERT OR REPLACE INTO keeper_games (
                    source_agent, game_title, platform, completion_rate, trophy_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "sly",
                    game_title,
                    settings.psn_platform,
                    float(telemetry.completion),
                    int(telemetry.trophies_total),
                    telemetry.fetched_at,
                ),
            )

            entity_key = f"{game_title}::{settings.psn_platform}"
            latest_payload = {
                "completion_rate": float(telemetry.completion),
                "trophy_count": int(telemetry.trophies_total),
                "correlation_id": telemetry.correlation_id,
            }
            _promote_snapshots(
                connection,
                entity_type="game",
                entity_key=entity_key,
                latest_payload_json=json.dumps(latest_payload, separators=(",", ":")),
                created_at=telemetry.fetched_at,
            )
