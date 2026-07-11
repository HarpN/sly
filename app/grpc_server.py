from __future__ import annotations

from concurrent import futures
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

import grpc
from google.protobuf import empty_pb2, json_format, struct_pb2

from .config import settings
from .judy_client import JudyClient
from .models import JudyProposal, SyncRequest
from .psn_client import PsnClient

metrics: dict[str, int] = {
    "requests_total": 0,
    "synced_total": 0,
    "judge_only_total": 0,
    "commit_total": 0,
}
_metrics_lock = Lock()

psn_client = PsnClient()
judy_client = JudyClient()


def _dict_to_struct(payload: dict[str, Any]) -> struct_pb2.Struct:
    message = struct_pb2.Struct()
    json_format.ParseDict(payload, message)
    return message


def _struct_to_dict(message: struct_pb2.Struct) -> dict[str, Any]:
    return json_format.MessageToDict(message)


def _health(_: empty_pb2.Empty, context: grpc.ServicerContext) -> struct_pb2.Struct:
    del context
    return _dict_to_struct(
        {
            "status": "ok",
            "service": settings.service_name,
            "transport": "grpc",
            "judy_grpc_target": settings.judy_grpc_target,
        }
    )


def _is_authorized(context: grpc.ServicerContext) -> bool:
    if not settings.inbound_auth_enabled:
        return True

    if not settings.inbound_auth_token:
        return False

    metadata = dict(context.invocation_metadata())
    token = metadata.get(settings.inbound_auth_header.lower())
    return token == settings.inbound_auth_token


def _sync_psn(request_message: struct_pb2.Struct, context: grpc.ServicerContext) -> struct_pb2.Struct:
    with _metrics_lock:
        metrics["requests_total"] += 1

    if not _is_authorized(context):
        context.set_code(grpc.StatusCode.UNAUTHENTICATED)
        context.set_details("Missing or invalid inbound authentication metadata")
        return struct_pb2.Struct()

    try:
        request = SyncRequest.model_validate(_struct_to_dict(request_message))
    except Exception as exc:
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(f"Invalid sync request: {exc}")
        return struct_pb2.Struct()

    telemetry = psn_client.fetch_telemetry(request)
    proposal = JudyProposal(
        transaction_metadata={
            "agent_id": settings.service_name,
            "timestamp": telemetry.fetched_at,
            "correlation_id": telemetry.correlation_id,
        },
        proposed_action={
            "target_table": "local_backlog",
            "action_type": "UPDATE_STATUS",
            "entity_id": request.account_id,
            "payload": {
                "status": "ACTIVE",
                "completion": telemetry.completion,
                "recently_played": telemetry.recently_played,
            },
        },
        agent_rationale="PSN telemetry synchronization",
        sync_telemetry=telemetry,
    )

    judy_response = judy_client.send_sync(proposal, commit=request.commit)

    with _metrics_lock:
        metrics["synced_total"] += 1
        if request.commit:
            metrics["commit_total"] += 1
        else:
            metrics["judge_only_total"] += 1

    return _dict_to_struct(
        {
            "correlation_id": telemetry.correlation_id,
            "commit": request.commit,
            "telemetry": telemetry.model_dump(),
            "proposal": proposal.model_dump(),
            "judy_response": judy_response,
        }
    )


def create_server(bind_address: str | None = None) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=settings.grpc_max_workers))
    handlers = {
        "Health": grpc.unary_unary_rpc_method_handler(
            _health,
            request_deserializer=empty_pb2.Empty.FromString,
            response_serializer=struct_pb2.Struct.SerializeToString,
        ),
        "SyncPSN": grpc.unary_unary_rpc_method_handler(
            _sync_psn,
            request_deserializer=struct_pb2.Struct.FromString,
            response_serializer=struct_pb2.Struct.SerializeToString,
        ),
    }
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler("sly.SlyService", handlers),))

    bind_target = bind_address or f"{settings.host}:{settings.grpc_port}"
    if settings.grpc_tls_enabled:
        with open(settings.grpc_tls_server_key_path, "rb") as key_file:
            private_key = key_file.read()
        with open(settings.grpc_tls_server_cert_path, "rb") as cert_file:
            certificate_chain = cert_file.read()

        root_certificates = None
        if settings.grpc_tls_client_ca_cert_path:
            with open(settings.grpc_tls_client_ca_cert_path, "rb") as ca_file:
                root_certificates = ca_file.read()

        credentials = grpc.ssl_server_credentials(
            [(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=settings.grpc_tls_require_client_auth,
        )
        bound_port = server.add_secure_port(bind_target, credentials)
    else:
        bound_port = server.add_insecure_port(bind_target)

    if not bound_port:
        raise RuntimeError("Failed to bind Sly gRPC server")
    server.bound_port = bound_port  # type: ignore[attr-defined]
    return server


def serve() -> None:
    server = create_server()
    server.start()
    server.wait_for_termination()
