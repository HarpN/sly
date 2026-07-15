# Sly

Sly is the PSN telemetry synchronization agent. It runs as a gRPC service, collects PSN profile state, packages it into a signed proposal, and forwards the proposal to Judy for governance review or commit.

## Architecture

Sly follows the same contract-first pattern as the other agents in this stack.

- `agent-zone`: Sly receives sync requests and builds PSN telemetry proposals.
- `governance-zone`: Judy receives signed proposals from Sly for review or commit.
- `transport`: gRPC with protobuf `Struct` payloads for portable cross-service contracts.
- `integrity`: HMAC-SHA256 signatures protect outbound requests.
- `runtime`: Python 3.12 on a slim container image.

## Service Flow

1. A client calls `SyncPSN` with an account and region.
2. Sly fetches or synthesizes PSN telemetry.
3. Sly builds a proposal envelope and signs it.
4. Sly sends the proposal to Judy over gRPC.
5. Judy returns the review or commit response.

## Environment

- `GRPC_PORT`: inbound gRPC port, default `50055`
- `GRPC_MAX_WORKERS`: gRPC thread pool size for concurrent request handling (default `32`)
- `JUDY_GRPC_TARGET`: Judy gRPC endpoint
- `JUDY_TLS_ENABLED`: use TLS for outbound Judy calls when set to `true`
- `JUDY_TLS_CA_CERT_PATH`: optional CA bundle path for Judy TLS validation
- `JUDY_MTLS_ENABLED`: enable client certificate auth for outbound Judy calls
- `JUDY_TLS_CLIENT_CERT_PATH`: client certificate file path for Judy mTLS
- `JUDY_TLS_CLIENT_KEY_PATH`: client private key file path for Judy mTLS
- `GRPC_TLS_ENABLED`: enable TLS listener for inbound Sly gRPC server
- `GRPC_TLS_SERVER_CERT_PATH`: server certificate file path for Sly TLS listener
- `GRPC_TLS_SERVER_KEY_PATH`: server private key file path for Sly TLS listener
- `GRPC_TLS_REQUIRE_CLIENT_AUTH`: require client certificate auth on inbound Sly listener
- `GRPC_TLS_CLIENT_CA_CERT_PATH`: trusted client CA bundle path for inbound client cert validation
- `OUTBOUND_SIGNATURE_SECRET`: HMAC secret used for outbound payload signing
- `OUTBOUND_SIGNATURE_HEADER`: metadata header used to carry the signature
- `REPLAY_TTL_SECONDS`: replay protection window in seconds (default `300`)
- `INBOUND_AUTH_ENABLED`: enforce inbound gRPC auth metadata check
- `INBOUND_AUTH_HEADER`: inbound metadata header key (default `x-sly-auth`)
- `INBOUND_AUTH_TOKEN`: required inbound metadata token value
- `PSN_ACCOUNT_ID`: default PSN account identifier
- `PSN_REGION`: default PSN region

## Local Run

```bash
python -m app.main
```

## Docker

```bash
docker build -t sly-psn-sync .
docker run --rm -p 50055:50055 sly-psn-sync
```

## Compose

```bash
docker compose up --build
```

### Compose mTLS Profile

Use the mTLS override file to start Sly with inbound TLS + client-auth and outbound mTLS to Judy.

Generate local dev certificates first:

```powershell
./scripts/generate-dev-certs.ps1 -Force
```

```bash
docker compose -f docker-compose.yml -f docker-compose.mtls.yml up --build
```

Place local certificates under `certs/` using the layout documented in `certs/README.md`.

Verify certificate chains and mTLS handshakes:

```powershell
./scripts/verify-mtls.ps1
```

If Sly/Judy are not currently running, verify cert trust only:

```powershell
./scripts/verify-mtls.ps1 -SkipHandshake
```

## Tests

```bash
pytest
```

## Validation And Conventions

- Local validation passes with `pytest` using the workspace venv Python interpreter.
- gRPC tests use an ephemeral bind port so they remain stable across machines.
- Sly keeps PSN telemetry separate from Milo's guide scraping store.
- Sly follows the same contract-first, signed-request template as the other agent repos.
- Outbound Judy calls include nonce and issued-at metadata with TTL validation.
- Inbound sync requests are rejected unless auth metadata matches configured token.
- mTLS can be enabled for Sly to Judy calls and for inbound Sly listeners when cert paths are configured.

## Updating This Repo

1. Keep changes scoped to the PSN telemetry boundary; do not merge Milo guide-scraping concerns into Sly.
2. Update the service contract, tests, and README together when behavior changes.
3. Re-run `pytest` after each implementation pass and confirm `git diff --check` stays clean.
4. Preserve the PSN telemetry flow and the Judy gRPC signing flow when extending the service.

## Helm

The Helm chart lives under `charts/sly` and deploys:

- a gRPC `Service`
- a `Deployment` with liveness/readiness TCP probes
- a `Secret` for the outbound signing key
- an egress `NetworkPolicy` that only allows traffic to Judy

## Notes

The PSN telemetry store is intentionally separate from the guide scraper that will be implemented in Milo. The two agents have different data shapes, retention needs, and sync cadences, so they should not share a database.

## Changelog

### v0.2.0 - 2026-07-14

Added:

- Alignment notes with the broader security hardening posture across agent services (auth metadata, signatures, replay protection, mTLS-ready runtime).

Changed:

- Clarified boundary position: Sly remains telemetry-focused while guide ingestion/moderation controls are isolated to Milo.
