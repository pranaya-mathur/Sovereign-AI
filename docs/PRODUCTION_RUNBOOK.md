# Sovereign-AI Production Deployment Runbook (Regulated BFSI/Healthcare)

## Prerequisites

- Kubernetes cluster (1.25+), Helm 3.x, kubectl access.
- Managed secrets provisioned: `database-url`, `jwt-secret-key`, `sovereign-api-key`, optional `groq-api-key`, optional `redis-url`.
- Postgres and Redis endpoints available (or in-cluster equivalents).
- TLS certificate and optional mTLS CA secret for ingress.

## Deployment Flow (Docker -> Helm)

1. Build and publish image:
   - `docker build -t <registry>/sovereign-ai:4.1.0 .`
   - `docker push <registry>/sovereign-ai:4.1.0`
2. Update Helm values:
   - set `image.repository`, `image.tag`, `secrets.name`, ingress hosts/TLS.
3. Install/upgrade:
   - `helm upgrade --install sovereign-ai deploy/helm/sovereign-ai -n sovereign-ai --create-namespace -f deploy/helm/sovereign-ai/values.yaml`

## Zero-Trust Secrets Checklist

- `JWT_SECRET_KEY` is unique, rotated, and stored in secret manager.
- `SOVEREIGN_API_KEY` is injected via secret and rotated per policy.
- No default credentials in runtime paths or dashboards.
- `STORE_RAW_LLM_RESPONSE=false` for DPDP minimization baseline.
- Public access disabled for production service endpoints.

## Migration for redacted_llm_response

1. Apply DB migration for `redacted_llm_response` column.
2. Backfill redacted content for historical rows if required:
   - read historical `llm_response`, apply `rules.pii_india.redact_india_pii`, write `redacted_llm_response`.
3. Validate row counts and sample masking quality.
4. Optionally rewrite `llm_response` with redacted text for strict minimization policy.

## Post-Deployment Smoke Tests

- `GET /health` returns healthy/degraded with DB check.
- `GET /api/monitoring/status` reports `4.1.0`.
- `POST /api/detect` with valid `x-api-key` succeeds.
- `POST /api/detect` without auth fails with 401.
- Metrics endpoint exposed and scraped by Prometheus.

## Monitoring and Alerting

- Track `http_requests_total`, request latency histograms, detection tier ratios.
- Alert on:
  - high-severity red-team bypasses
  - sustained Tier-3 spike (drift signal)
  - auth failures spike
  - error-rate and latency SLO breaches

## Rollback Plan

1. Helm rollback:
   - `helm rollback sovereign-ai <revision> -n sovereign-ai`
2. Restore previous image tag and values if needed.
3. Verify health and authentication controls post-rollback.
4. Preserve compliance artifacts and incident timeline.

## Compliance Evidence Checklist

- Deployment manifest and Helm values for release.
- Secret rotation evidence for JWT/API key.
- Redaction-at-rest policy and migration evidence.
- OTel/Prometheus dashboards and alert snapshots.
- Red-team report artifact (`tests/redteam/redteam_report.json`) and pass/fail gate output.
- ADR references (`docs/adr/*`) linked to control design decisions.
