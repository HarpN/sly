from __future__ import annotations

import os


class Settings:
    environment: str = os.getenv("ENVIRONMENT", "dev")
    service_name: str = os.getenv("SERVICE_NAME", "sly-psn-sync")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")
    host: str = os.getenv("HOST", "0.0.0.0")
    grpc_port: int = int(os.getenv("GRPC_PORT", "50055"))
    grpc_max_workers: int = int(os.getenv("GRPC_MAX_WORKERS", "32"))

    judy_grpc_target: str = os.getenv("JUDY_GRPC_TARGET", "judy-council:50052")
    judy_timeout_seconds: float = float(os.getenv("JUDY_TIMEOUT_SECONDS", "10"))
    judy_tls_enabled: bool = os.getenv("JUDY_TLS_ENABLED", "false").lower() == "true"
    judy_tls_ca_cert_path: str = os.getenv("JUDY_TLS_CA_CERT_PATH", "")
    judy_mtls_enabled: bool = os.getenv("JUDY_MTLS_ENABLED", "false").lower() == "true"
    judy_tls_client_cert_path: str = os.getenv("JUDY_TLS_CLIENT_CERT_PATH", "")
    judy_tls_client_key_path: str = os.getenv("JUDY_TLS_CLIENT_KEY_PATH", "")

    grpc_tls_enabled: bool = os.getenv("GRPC_TLS_ENABLED", "false").lower() == "true"
    grpc_tls_server_cert_path: str = os.getenv("GRPC_TLS_SERVER_CERT_PATH", "")
    grpc_tls_server_key_path: str = os.getenv("GRPC_TLS_SERVER_KEY_PATH", "")
    grpc_tls_client_ca_cert_path: str = os.getenv("GRPC_TLS_CLIENT_CA_CERT_PATH", "")
    grpc_tls_require_client_auth: bool = os.getenv("GRPC_TLS_REQUIRE_CLIENT_AUTH", "false").lower() == "true"

    outbound_signature_header: str = os.getenv("OUTBOUND_SIGNATURE_HEADER", "X-Sly-Signature")
    outbound_signature_secret: str = os.getenv("OUTBOUND_SIGNATURE_SECRET", "")
    outbound_key_id: str = os.getenv("OUTBOUND_KEY_ID", "sly-k1")
    outbound_signature_dev_fallback: str = "sly-dev-secret"

    replay_ttl_seconds: int = int(os.getenv("REPLAY_TTL_SECONDS", "300"))

    inbound_auth_enabled: bool = os.getenv("INBOUND_AUTH_ENABLED", "true").lower() == "true"
    inbound_auth_token: str = os.getenv("INBOUND_AUTH_TOKEN", "")
    inbound_auth_header: str = os.getenv("INBOUND_AUTH_HEADER", "x-sly-auth")

    source_account_id: str = os.getenv("PSN_ACCOUNT_ID", "demo-account")
    source_region: str = os.getenv("PSN_REGION", "us")
    keeper_db_path: str = os.getenv("KEEPER_DB_PATH", "../TheKeeper/keeper_blended.db")
    keeper_export_enabled: bool = os.getenv("KEEPER_EXPORT_ENABLED", "true").lower() == "true"
    psn_platform: str = os.getenv("PSN_PLATFORM", "PS5")


settings = Settings()
