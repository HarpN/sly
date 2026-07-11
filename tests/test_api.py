from __future__ import annotations

import os
from datetime import datetime, timezone

import grpc
import pytest
from google.protobuf import empty_pb2, json_format, struct_pb2

os.environ["JUDY_GRPC_TARGET"] = "127.0.0.1:50066"
os.environ["OUTBOUND_SIGNATURE_SECRET"] = "sly-dev-secret"
os.environ["INBOUND_AUTH_TOKEN"] = "test-sly-auth-token"

from app.grpc_server import create_server, judy_client, psn_client
from app.models import SyncTelemetry


@pytest.fixture(scope="module")
def channel() -> grpc.Channel:
    server = create_server(bind_address="127.0.0.1:0")
    server.start()

    grpc_channel = grpc.insecure_channel(f"127.0.0.1:{server.bound_port}")
    grpc.channel_ready_future(grpc_channel).result(timeout=5)

    yield grpc_channel

    grpc_channel.close()
    server.stop(None)


def _sync_call(channel: grpc.Channel):
    return channel.unary_unary(
        "/sly.SlyService/SyncPSN",
        request_serializer=struct_pb2.Struct.SerializeToString,
        response_deserializer=struct_pb2.Struct.FromString,
    )


def _sync_metadata() -> tuple[tuple[str, str], ...]:
    return (("x-sly-auth", "test-sly-auth-token"),)


def test_health(channel: grpc.Channel) -> None:
    response = channel.unary_unary(
        "/sly.SlyService/Health",
        request_serializer=empty_pb2.Empty.SerializeToString,
        response_deserializer=struct_pb2.Struct.FromString,
    )(empty_pb2.Empty())
    payload = json_format.MessageToDict(response)
    assert payload["status"] == "ok"
    assert payload["transport"] == "grpc"


def test_sync_judge_mode(channel: grpc.Channel, monkeypatch) -> None:
    monkeypatch.setattr(
        psn_client,
        "fetch_telemetry",
        lambda request: SyncTelemetry(
            account_id=request.account_id,
            region=request.region,
            fetched_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            correlation_id="sly-test-001",
            trophies_total=100,
            trophies_earned=80,
            completion=80,
            recently_played=["Astro Bot"],
            raw_payload={"source_account_id": request.account_id},
        ),
    )
    monkeypatch.setattr(judy_client, "send_sync", lambda proposal, commit: {"final_verdict": "APPROVED", "council_id": "cncl-1"})

    request = struct_pb2.Struct()
    json_format.ParseDict({"account_id": "demo-account", "region": "us", "commit": False}, request)
    response = json_format.MessageToDict(_sync_call(channel)(request, metadata=_sync_metadata()))

    assert response["commit"] is False
    assert response["judy_response"]["final_verdict"] == "APPROVED"
    assert response["telemetry"]["account_id"] == "demo-account"


def test_sync_commit_mode(channel: grpc.Channel, monkeypatch) -> None:
    monkeypatch.setattr(judy_client, "send_sync", lambda proposal, commit: {"committed": True, "decision": {"final_verdict": "APPROVED"}})

    request = struct_pb2.Struct()
    json_format.ParseDict({"account_id": "demo-account", "region": "us", "commit": True}, request)
    response = json_format.MessageToDict(_sync_call(channel)(request, metadata=_sync_metadata()))

    assert response["commit"] is True
    assert response["judy_response"]["committed"] is True


def test_sync_requires_auth(channel: grpc.Channel) -> None:
    request = struct_pb2.Struct()
    json_format.ParseDict({"account_id": "demo-account", "region": "us", "commit": False}, request)

    with pytest.raises(grpc.RpcError) as rpc_error:
        _sync_call(channel)(request)

    assert rpc_error.value.code() == grpc.StatusCode.UNAUTHENTICATED
