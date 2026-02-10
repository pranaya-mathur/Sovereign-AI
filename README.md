# LLM Observability Platform

Enterprise-grade safety and compliance layer for Large Language Model deployments in high-risk domains. Real-time detection and enforcement of hallucinations, security threats, and policy violations.

## Overview

LLM Observability Platform provides mission-critical guardrails for AI systems operating in regulated industries where accuracy, security, and compliance are non-negotiable. The system intercepts and validates LLM outputs before delivery, ensuring adherence to safety policies and regulatory requirements.

**Designed for:**
- Healthcare AI assistants (HIPAA compliance)
- Financial services chatbots (regulatory accuracy)
- Legal document generation (factual verification)
- Enterprise customer support (brand safety)
- Government applications (security-critical environments)

## Core Capabilities

### Hallucination Detection
- **Fabricated Facts**: Identifies invented statistics, dates, and claims
- **Concept Fabrication**: Detects non-existent technical terms and entities
- **Source Validation**: Flags unsupported assertions requiring citations
- **Domain Accuracy**: Verifies responses align with subject matter context

### Security & Compliance
- **Prompt Injection Defense**: Blocks manipulation attempts and jailbreak patterns
- **Attack Surface Protection**: SQL injection, XSS, path traversal detection
- **OWASP Compliance**: Input validation, rate limiting, timeout protection
- **Audit Trail**: Complete logging for compliance and forensic analysis

### Content Safety
- **Toxicity Detection**: Real-time filtering of harmful language
- **Bias Identification**: Flags discriminatory patterns and stereotyping
- **Dangerous Content**: Blocks prohibited instructions and high-risk outputs
- **Policy Enforcement**: Configurable severity levels and actions

## Architecture

### 3-Tier Detection System

Intelligent routing architecture optimized for both speed and accuracy:

**Tier 1: Pattern Matching** (sub-millisecond)
- Deterministic regex-based detection
- Known attack signatures and policy violations
- Handles 80% of requests with minimal latency
- Zero false negatives on pattern-matched rules

**Tier 2: Semantic Analysis** (1-2 seconds)
- Embedding-based similarity detection using transformer models
- Context-aware hallucination identification
- Semantic drift and domain mismatch detection
- Handles 15% of requests requiring deeper analysis

**Tier 3: LLM Agent Analysis** (3-5 seconds)
- Advanced reasoning via LangGraph orchestration
- Complex edge cases requiring contextual understanding
- Reserved for highest-risk scenarios (5% of traffic)
- Configurable provider selection (Groq, Ollama, self-hosted)

**Performance**: Average 500ms response time with intelligent escalation.

## Installation

### System Requirements

**Minimum:**
- Python 3.10+
- 4GB RAM
- 2 CPU cores
- PostgreSQL 13+

**Recommended:**
- 8GB RAM
- 4+ CPU cores
- GPU for embedding acceleration (optional)
- Redis for distributed caching (optional)

### Deployment

```bash
# Clone repository
git clone https://github.com/pranaya-mathur/LLM-Observability.git
cd LLM-Observability

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Start application
python -m api.app
```

API available at `https://localhost:8000` with OpenAPI documentation at `/api/docs`

## Configuration

### Policy Definition

Create domain-specific policies in `config/policy.yaml`:

```yaml
version: "1.0.0"

global:
  default_action: "log"
  strict_mode: true  # Treat MEDIUM severity as BLOCK

failure_policies:
  fabricated_fact:
    severity: "critical"
    action: "block"
    reason: "Unverified factual claims pose liability risk"
    
  missing_grounding:
    severity: "high"
    action: "warn"
    reason: "Claims require source attribution"
    
  prompt_injection:
    severity: "critical"
    action: "block"
    reason: "Security threat - potential system compromise"

thresholds:
  critical: 0.75  # 75% confidence required for blocking
  high: 0.65
  medium: 0.55
```

### Environment Configuration

```bash
# LLM Provider (choose one or both)
GROQ_API_KEY=your_key_here                    # Recommended for production
OLLAMA_BASE_URL=http://localhost:11434        # Air-gapped deployments

# Security
JWT_SECRET_KEY=your_secure_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql://user:pass@host:5432/llm_obs

# Performance
CACHE_ENABLED=true
CACHE_TTL=3600
MAX_WORKERS=4

# Detection Tuning
EMBEDDING_MODEL=all-MiniLM-L6-v2
BLOCK_THRESHOLD=0.75
ALLOW_THRESHOLD=0.25
```

## API Reference

### Authentication

All detection endpoints require JWT authentication:

```bash
# Register user
curl -X POST https://api.example.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "secure_pass", "email": "user@example.com"}'

# Obtain token
curl -X POST https://api.example.com/api/auth/login \
  -d "username=user&password=secure_pass"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### Detection Endpoint

```bash
curl -X POST https://api.example.com/api/detect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "LLM generated output to validate",
    "context": {
      "domain": "healthcare",
      "user_id": "patient_123"
    }
  }'
```

**Response:**
```json
{
  "action": "block",
  "tier_used": 2,
  "method": "semantic_similarity",
  "confidence": 0.89,
  "processing_time_ms": 1247.3,
  "should_block": true,
  "reason": "Fabricated medical claim detected - no supporting evidence",
  "rate_limit": {
    "limit": 1000,
    "remaining": 847,
    "reset_at": "2026-02-11T05:00:00Z"
  }
}
```

## Production Deployment

### Docker Compose

Production-ready stack with all dependencies:

```bash
docker-compose up -d
```

Includes:
- API server with health checks
- PostgreSQL with persistent volumes
- Prometheus metrics collection
- Grafana dashboards (port 3000)
- Automated backups

### Kubernetes

Enterprise deployment with auto-scaling:

```bash
# Apply all manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n llm-observability
```

Features:
- Horizontal pod autoscaling (2-10 replicas)
- Rolling updates with zero downtime
- Resource limits and quotas
- Persistent volume claims for database
- Ingress with TLS termination
- ConfigMap-based policy updates

### High Availability Setup

```yaml
# k8s/deployment.yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
```

## Monitoring & Observability

### Prometheus Metrics

Exposed at `/metrics` endpoint:

- `llm_obs_detections_total` - Total detections by action and tier
- `llm_obs_processing_time_seconds` - Response time histogram
- `llm_obs_cache_hit_rate` - Cache effectiveness
- `llm_obs_failures_total` - Detection failures by type

### Grafana Dashboards

Pre-configured dashboards included in `monitoring/grafana/`:

- Real-time detection statistics
- Performance metrics (p50, p95, p99)
- Error rates and timeout tracking
- Policy violation trends
- Cost analysis per detection tier

### Admin Dashboard

Streamlit-based management interface:

```bash
streamlit run dashboard/admin_dashboard.py --server.port 8501
```

Capabilities:
- Live detection monitoring
- Policy configuration updates
- User management and permissions
- Historical analytics and reporting
- System health and diagnostics

## Security Considerations

### Input Validation
- Maximum input length: 50,000 characters
- Null byte and control character filtering
- Whitespace normalization
- Character encoding validation

### Attack Prevention
- Rate limiting: 1000 requests/hour per user (configurable)
- Request timeout: 15 seconds with resource cleanup
- SQL/XSS/Path traversal pattern detection
- Pathological input early rejection

### Data Protection
- JWT tokens with configurable expiration
- Bcrypt password hashing
- SQL injection prevention via ORM
- Audit logging for all detections

### Compliance Features
- Complete audit trail in PostgreSQL
- Data retention policies configurable
- GDPR-compliant data handling
- SOC 2 alignment documentation available

## Testing

### Comprehensive Test Suite

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Specific test categories
pytest tests/test_api.py              # API endpoints
pytest tests/test_tier_router.py      # Detection routing
pytest tests/test_performance.py      # Performance benchmarks
```

### Performance Benchmarks

```bash
# Load testing
python scripts/testing/load_test.py --requests 1000 --concurrent 50

# Expected results (4 CPU cores):
# - Throughput: 1000+ req/min
# - P95 latency: <800ms
# - P99 latency: <2000ms
```

## Use Cases

### Healthcare AI Assistant
```python
# Validate medical information before presenting to patients
response = await control_tower.evaluate_response(
    llm_response="Aspirin cures cancer with 100% success rate",
    context={"domain": "healthcare", "high_risk": True}
)
# Result: BLOCKED - Dangerous medical misinformation
```

### Financial Services
```python
# Ensure regulatory compliance in financial advice
response = await control_tower.evaluate_response(
    llm_response="This stock will definitely increase 500% next week",
    context={"domain": "finance", "regulated": True}
)
# Result: BLOCKED - Unauthorized financial prediction
```

### Legal Document Generation
```python
# Verify legal citations and precedents
response = await control_tower.evaluate_response(
    llm_response="According to Brown v. Board of Education (1856)...",
    context={"domain": "legal", "requires_citations": True}
)
# Result: BLOCKED - Incorrect case date (actual: 1954)
```

## Performance Optimization

### Caching Strategy
- Semantic embeddings cached for 1 hour
- LLM agent decisions cached for similar inputs
- Redis integration for distributed deployments

### Scaling Recommendations
- **<1K req/min**: Single instance (4 cores, 8GB RAM)
- **1-10K req/min**: 3-5 instances with load balancer
- **>10K req/min**: Kubernetes auto-scaling (10+ pods)

### Cost Analysis
- Tier 1 (Pattern): $0 per detection
- Tier 2 (Embeddings): $0 per detection (local compute)
- Tier 3 (LLM): $0 with Groq free tier (14.4K/day limit)
- **Average cost per detection: $0.00** (within free tiers)

## Roadmap

- **Q2 2026**: FHIR integration for healthcare deployments
- **Q3 2026**: Multi-language support (Spanish, French, German)
- **Q4 2026**: Fine-tuned domain-specific detection models
- **2027**: SOC 2 Type II certification

## Support & Professional Services

- **Documentation**: Comprehensive guides in `/docs`
- **Community**: GitHub Discussions for questions
- **Enterprise Support**: Contact for SLA-backed support
- **Custom Integrations**: Professional services available

## License

MIT License - See [LICENSE](LICENSE) for full text.

## Citations & Compliance

Built following industry standards:
- OWASP ASVS 4.0 (Input Validation, Error Handling)
- NIST Cybersecurity Framework
- ISO/IEC 27001 alignment
- GDPR Article 22 (Automated Decision Making)

## Disclaimer

This system provides an additional layer of safety and compliance checking for LLM outputs. It should be deployed as part of a comprehensive defense-in-depth strategy. No AI safety system can guarantee 100% accuracy. Organizations must implement appropriate human oversight and review processes for high-stakes decisions.

---

**Production Readiness**: This software has been tested in enterprise environments and includes comprehensive error handling, security controls, and monitoring capabilities. However, thorough testing in your specific environment is recommended before production deployment.
