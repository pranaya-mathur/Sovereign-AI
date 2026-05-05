# ADR-002: Data Minimization, Redaction at Rest, and Compliance Audit

- **Status**: Accepted
- **Date**: 2026-05-05

## Context

LLM outputs can contain personal data (Aadhaar, PAN, phone, UPI-like identifiers). Persisting raw outputs by default increases privacy and breach risk.

## Decision

1. Add `redacted_llm_response` persistence field.
2. Redact text using `rules.pii_india.redact_india_pii` before storage.
3. Default to storing redacted response in `llm_response` unless explicitly overridden with `STORE_RAW_LLM_RESPONSE=true`.
4. Keep append-style compliance audit trail with hash-centric payloads.

## Control Mapping

- **DPDP 2023**: Data minimization, purpose limitation, protective processing controls.
- **RBI/SEBI**: Sensitive customer data handling, auditable control evidence.
- **SOC 2 Confidentiality**: Reduced sensitive data persistence and improved at-rest protection baseline.

## Consequences

- Forensic raw text is no longer persisted by default; operators must explicitly opt in.
- Reporting and analytics should use redacted fields for governance dashboards and exports.
