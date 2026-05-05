# ADR-001: Zero-Trust Authentication and Secret Management

- **Status**: Accepted
- **Date**: 2026-05-05

## Context

Sovereign-AI serves regulated BFSI and Healthcare workloads with high security requirements. Public or weakly authenticated endpoints and embedded default credentials are not acceptable for production.

## Decision

1. Enforce zero-trust route protection in API runtime:
   - Require either `x-api-key` or Bearer JWT for protected routes.
   - Keep only operationally necessary public paths (`/health`, docs, metrics root paths).
2. Remove runtime default users and seeded credentials.
3. Remove unauthenticated Cloud Run deployment flags.
4. Standardize Kubernetes secret injection via `secretKeyRef`.

## Control Mapping

- **DPDP 2023**: Access control supports lawful processing boundaries and unauthorized access prevention.
- **RBI/SEBI**: Strong identity and access controls for critical systems; reduced operational attack surface.
- **SOC 2 Security**: Logical access controls, secure configuration management, secret handling.
- **Zero-Trust**: Never trust by network location; verify each request identity.

## Consequences

- Deployment requires external secret provisioning (`JWT_SECRET_KEY`, `SOVEREIGN_API_KEY`).
- Existing clients must include API key or JWT for protected endpoints.
- Security posture improved with minimal impact on core detection logic.
