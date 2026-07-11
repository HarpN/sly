from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .config import settings
from .models import SyncRequest, SyncTelemetry


class PsnClient:
    def fetch_telemetry(self, request: SyncRequest) -> SyncTelemetry:
        fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        recently_played = ["Astro Bot", "Helldivers 2", "Gran Turismo 7"]
        trophies_total = 125
        trophies_earned = 92
        completion = int(trophies_earned / trophies_total * 100) if trophies_total > 0 else 0

        return SyncTelemetry(
            account_id=request.account_id,
            region=request.region,
            fetched_at=fetched_at,
            correlation_id=f"sly-{uuid4().hex[:12]}",
            trophies_total=trophies_total,
            trophies_earned=trophies_earned,
            completion=completion,
            recently_played=recently_played,
            raw_payload={
                "source_account_id": settings.source_account_id,
                "source_region": settings.source_region,
                "discovered_game_count": len(recently_played),
            },
        )
