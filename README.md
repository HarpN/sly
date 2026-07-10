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
- `JUDY_GRPC_TARGET`: Judy gRPC endpoint
- `OUTBOUND_SIGNATURE_SECRET`: HMAC secret used for outbound payload signing
- `OUTBOUND_SIGNATURE_HEADER`: metadata header used to carry the signature
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

## Tests

```bash
pytest
```

## Validation And Conventions

- Local validation passes with `pytest` using the workspace venv Python interpreter.
- gRPC tests use an ephemeral bind port so they remain stable across machines.
- Sly keeps PSN telemetry separate from Milo's guide scraping store.
- Sly follows the same contract-first, signed-request template as the other agent repos.

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
