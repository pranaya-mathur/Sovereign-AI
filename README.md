# Sovereign AI - LLM Observability Platform

Production-ready safety and compliance layer for Large Language Model deployments in high-risk domains. Provides real-time risk detection and policy enforcement for LLM outputs.

## Overview

Sovereign AI offers guardrails for AI systems operating in regulated industries where accuracy, security, and compliance are critical. The system analyzes LLM outputs and flags potential risks before delivery, supporting adherence to safety policies and regulatory requirements.

**Designed for:**
- Healthcare AI assistants (HIPAA considerations)
- Financial services chatbots (regulatory compliance)
- Legal document generation (accuracy verification)
- Enterprise customer support (brand safety)
- Government applications (security-sensitive environments)

## Core Capabilities

### Risk Detection
- **Potential Fabrications**: Flags suspicious claims, statistics, and assertions
- **Concept Validation**: Detects potentially invented terms and entities
- **Source Attribution**: Identifies unsupported assertions requiring citations
- **Domain Alignment**: Checks if responses align with expected subject matter

### Security Monitoring
- **Prompt Injection Detection**: Identifies manipulation attempts and jailbreak patterns
- **Attack Pattern Recognition**: SQL injection, XSS, path traversal detection
- **Input Validation**: OWASP-aligned input sanitization and rate limiting
- **Audit Trail**: Comprehensive logging for compliance and forensic review

### Content Safety
- **Toxicity Screening**: Filters potentially harmful language
- **Bias Detection**: Flags potentially discriminatory patterns
- **Policy Compliance**: Configurable severity levels and enforcement actions
- **Risk Categorization**: Critical, high, medium, and low risk classifications

## Architecture

### 3-Tier Detection System

Intelligent routing architecture balancing speed and depth of analysis:

**Tier 1: Pattern Matching** (sub-millisecond)
- Deterministic regex-based detection
- Known attack signatures and policy violations
- Processes approximately 80% of requests
- Minimal latency overhead

**Tier 2: Semantic Analysis** (1-2 seconds)
- Embedding-based similarity detection using transformer models
- Context-aware risk identification
- Semantic drift and domain mismatch detection
- Handles approximately 15% of requests

**Tier 3: LLM Agent Analysis** (3-5 seconds)
- Advanced reasoning via LangGraph orchestration
- Complex edge cases requiring contextual understanding
- Used for approximately 5% of highest-risk scenarios
- Configurable provider selection (Groq, Ollama, self-hosted)

**Typical Performance**: Average ~500ms response time with intelligent escalation.

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
git clone https://github.com/pranaya-mathur/Sovereign-AI.git
cd Sovereign-AI

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

API available at `http://localhost:8000` with OpenAPI documentation at `/api/docs`

## Configuration

### Policy Definition

Define domain-specific policies in `config/policy.yaml`:

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
  critical: 0.75  # 75% confidence threshold for blocking
  high: 0.65
  medium: 0.55
```

### Environment Configuration

```bash
# LLM Provider (choose one or both)
GROQ_API_KEY=your_key_here                    # Recommended - free tier available
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

Detection endpoints require JWT authentication:

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "secure_pass", "email": "user@example.com"}'

# Obtain token
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=user&password=secure_pass"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### Detection Endpoint

```bash
curl -X POST http://localhost:8000/api/detect \
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
  "reason": "Potential fabricated medical claim - requires verification",
  "rate_limit": {
    "limit": 1000,
    "remaining": 847,
    "reset_at": "2026-02-11T05:00:00Z"
  }
}
```

## Production Deployment

### Docker Compose

Development and staging deployment:

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

Production deployment with scaling:

```bash
# Apply all manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n llm-observability
```

Features:
- Horizontal pod autoscaling (2-10 replicas)
- Rolling updates with minimal downtime
- Resource limits and requests defined
- Persistent volume claims for database
- Ingress configuration included
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

## Understanding Observability vs Enforcement

**This is an observability system first, enforcement tool second:**

### Observability Features
- **Detection & Logging**: All outputs are analyzed and logged
- **Risk Scoring**: Confidence scores and reasoning provided
- **Metrics & Analytics**: Track patterns, trends, and model behavior
- **Audit Trail**: Complete history for compliance review

### Enforcement Options (Configurable)
- **Block**: Prevent high-risk outputs from delivery (optional)
- **Warn**: Flag concerns but allow delivery with context
- **Log**: Record for review without user-facing impact

The system can operate in pure observability mode (log-only) or with active enforcement based on your risk tolerance and deployment needs.

## Security Considerations

### Input Validation
- Maximum input length: 50,000 characters
- Null byte and control character filtering
- Whitespace normalization
- Character encoding validation

### Attack Prevention
- Configurable rate limiting per user (default: 1000 requests/hour)
- Request timeout: 15 seconds with resource cleanup
- SQL/XSS/Path traversal pattern detection
- Pathological input early rejection

### Data Protection
- JWT tokens with configurable expiration
- Bcrypt password hashing
- Parameterized queries via ORM
- Comprehensive audit logging

### Compliance Support
- Audit trail stored in PostgreSQL
- Configurable data retention policies
- GDPR-aligned data handling
- Documentation aligned with SOC 2 controls

## Testing

### Test Suite

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

# Typical results (4 CPU cores):
# - Throughput: ~1000 req/min
# - P95 latency: ~800ms
# - P99 latency: ~2000ms
```

## Use Cases

### Healthcare AI Assistant
```python
# Flag potentially risky medical information
response = await control_tower.evaluate_response(
    llm_response="Aspirin cures cancer with 100% success rate",
    context={"domain": "healthcare", "high_risk": True}
)
# Result: BLOCKED - High confidence dangerous medical misinformation
```

### Financial Services
```python
# Detect unauthorized financial predictions
response = await control_tower.evaluate_response(
    llm_response="This stock will definitely increase 500% next week",
    context={"domain": "finance", "regulated": True}
)
# Result: BLOCKED - Unauthorized definitive financial prediction
```

### Legal Document Generation
```python
# Verify legal citations
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
- Redis integration available for distributed deployments

### Scaling Recommendations
- **<1K req/min**: Single instance (4 cores, 8GB RAM)
- **1-10K req/min**: 3-5 instances with load balancer
- **>10K req/min**: Kubernetes auto-scaling (10+ pods)

### Cost Considerations
- Tier 1 (Pattern): Negligible compute cost
- Tier 2 (Embeddings): Local compute only
- Tier 3 (LLM): Free tier available with Groq (14,400 requests/day)
- Hosting costs depend on infrastructure choices

## Roadmap

- **Q2 2026**: FHIR integration for healthcare workflows
- **Q3 2026**: Multi-language support (Spanish, French, German)
- **Q4 2026**: Domain-specific detection model training
- **2027**: Enhanced compliance reporting features

## Support

- **Documentation**: Additional guides available in `/docs`
- **Community**: GitHub Issues for questions and bug reports
- **Contributing**: Pull requests welcome - see contributing guidelines

## License

MIT License - See [LICENSE](LICENSE) for full text.

## Standards Alignment

Development informed by:
- OWASP ASVS 4.0 (Input Validation, Error Handling)
- NIST Cybersecurity Framework
- ISO/IEC 27001 security controls
- GDPR Article 22 (Automated Decision Making)

## Important Disclaimers

**Detection Accuracy**: This system uses pattern matching, semantic analysis, and LLM-based reasoning to detect potential risks. Detection accuracy varies by content type and configuration. False positives and false negatives will occur.

**Not a Replacement for Human Review**: This tool is designed to augment, not replace, human oversight. Organizations must implement appropriate review processes for high-stakes decisions.

**Configuration Required**: Out-of-box detection policies are starting points. Tune thresholds and policies based on your specific use case, risk tolerance, and testing.

**Deployment Responsibility**: While the system includes security controls and follows best practices, deploying organizations are responsible for:
- Proper environment configuration and hardening
- Regular security updates and patches
- Appropriate access controls and monitoring
- Testing in their specific environment before production use
- Compliance with applicable regulations

**No Guarantees**: This software is provided "as is" per the MIT License. No warranties are made regarding detection accuracy, uptime, or suitability for any particular purpose.

---

**Status**: This software has been developed with production deployment in mind and includes comprehensive error handling, security controls, and monitoring. However, thorough evaluation and testing in your specific environment is essential before production use.
