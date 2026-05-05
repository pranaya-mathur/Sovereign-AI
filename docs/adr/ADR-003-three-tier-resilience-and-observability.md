# ADR-003: Three-Tier Resilience and Observability Hardening

- **Status**: Accepted
- **Date**: 2026-05-05

## Context

Production-grade guardrails require deterministic behavior under degraded provider conditions and clear observability for incident response and governance.

## Decision

1. Replace daemon-thread timeout behavior with asyncio timeout/cancellation semantics in core utility path.
2. Introduce standardized provider resilience:
   - retry with backoff
   - circuit breaker state per provider
3. Refactor monolithic control-tower enrichment and moderation fusion into dedicated modules:
   - `enforcement/enrichment.py`
   - `enforcement/moderation_fusion.py`
   - `enforcement/output_correction.py`
4. Keep public `ControlTowerV3` API and 3-tier policy behavior unchanged.
5. Keep OTel and Prometheus integration as first-class operational controls.

## Control Mapping

- **RBI/SEBI**: Operational resilience, model risk control, and monitoring traceability.
- **SOC 2 Availability**: Fault tolerance and graceful degradation under third-party failures.
- **SOC 2 Security**: Structured telemetry supports incident response and control verification.

## Consequences

- External moderation provider outages are less likely to cascade into system instability.
- Detection flow is easier to reason about and test due to reduced single-file complexity.
- Runtime resilience behavior is explicit and tunable.
