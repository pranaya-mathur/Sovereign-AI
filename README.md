# Sovereign AI - LLM Observability Platform

Production-ready safety and compliance layer for Large Language Model deployments in high-risk domains. Provides real-time risk detection and policy enforcement for LLM outputs through a signals-based detection pipeline.

## Overview

Sovereign AI offers guardrails for AI systems operating in regulated industries where accuracy, security, and compliance are critical. The system analyzes LLM outputs through parallel signal extraction, rule-based evaluation, and configurable enforcement actions.

**Designed for:**
- Healthcare AI assistants (HIPAA considerations)
- Financial services chatbots (regulatory compliance)
- Legal document generation (accuracy verification)
- Enterprise customer support (brand safety)
- Government applications (security-sensitive environments)

## Core Capabilities

### Risk Detection
- **Fabrication Detection**: Identifies potentially invented facts, concepts, and entities
- **Grounding Validation**: Detects claims lacking proper source attribution
- **Domain Alignment**: Flags responses that drift from expected subject matter
- **Confidence Analysis**: Identifies overconfident or hedging language patterns

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

### Signal-Rule-Enforcement Pipeline

Sovereign AI uses a modular detection architecture with three distinct stages:

#### Stage 1: Signal Extraction (Parallel Analysis)

Multiple signal detectors analyze the LLM response simultaneously:

**Domain Signals**
- `DomainMismatchSignal`: Detects semantic drift from expected domain
- `FabricatedConceptSignal`: Identifies potentially invented terms and concepts

**Grounding Signals**
- `MissingGroundingSignal`: Flags unsubstantiated claims requiring citations
- Uses embedding-based similarity to detect unsupported assertions

**Confidence Signals**
- `OverconfidenceSignal`: Detects absolute language without proper support
- Pattern matching for hedging and certainty indicators

**Pattern-Based Signals**
- Regex-based detection for known attack patterns
- Security vulnerability scanning (SQL injection, XSS, path traversal)

#### Stage 2: Rule Evaluation

Extracted signals are evaluated through a rules engine:

**Semantic Rules** (`rules/semantic_rules.py`)
- `HighRiskSemanticHallucinationRule`: Combines multiple signals for hallucination detection
- `FabricatedConceptRule`: Evaluates concept fabrication severity

**LLM-Based Rules** (`rules/llm_rules.py`)
- `HighConfidenceDomainMismatchRule`: Deep analysis for domain alignment
- Invoked for complex edge cases requiring contextual understanding

**Rule Execution**
- Rules are evaluated in severity order (critical → high → medium)
- Each rule generates a `Verdict` with severity and failure classification
- Multiple verdicts can be produced from a single analysis

#### Stage 3: Enforcement

**Verdict Adaptation** (`enforcement/verdict_adapter.py`)
- Converts rule verdicts into enforcement actions
- Severity mapping: CRITICAL/HIGH → BLOCK, MEDIUM/LOW → WARN/LOG

**Action Enforcement** (`enforcement/actions.py`)
- `BLOCK`: Prevents delivery of high-risk responses
- `ALLOW`: Permits response with optional logging
- `WARN`: Flags concern but allows delivery

**Control Tower** (`enforcement/control_tower_v3.py`)
- Orchestrates the entire detection pipeline
- Manages tier-based routing and performance optimization
- Tracks metrics and health statistics

### System Components

**Core Modules**
- `core/interceptor.py`: LLM request/response interception
- `core/context.py`: Request context management
- `core/events.py`: Event handling and dispatching
- `core/logger.py`: Structured logging
- `core/metrics.py`: Performance and detection metrics

**Signal System**
- `signals/runner.py`: Executes all registered signals in parallel
- `signals/registry.py`: Central signal registration
- `signals/base.py`: Base signal interface
- `signals/domain/`: Domain-specific signal detectors
- `signals/grounding/`: Citation and grounding signals
- `signals/confidence/`: Confidence analysis signals
- `signals/embeddings/`: Embedding-based semantic analysis
- `signals/regex/`: Pattern-based detection

**Rule Engine**
- `rules/engine.py`: Rule evaluation orchestration
- `rules/base.py`: Base rule interface
- `rules/semantic_rules.py`: Embedding-based rules
- `rules/llm_rules.py`: LLM-powered deep analysis rules
- `rules/verdicts.py`: Verdict data structures
- `rules/verdict_reducer.py`: Multi-verdict consolidation

**Enforcement Layer**
- `enforcement/enforcer.py`: Action execution
- `enforcement/tier_router.py`: Intelligent tier routing
- `enforcement/verdict_adapter.py`: Verdict-to-action mapping
- `enforcement/control_tower_v3.py`: Pipeline orchestration
- `enforcement/fallbacks/`: Graceful degradation strategies

**API Layer**
- `api/main.py`: FastAPI application
- `api/models.py`: Request/response schemas
- `api/routes/`: API endpoint definitions
- `api/middleware/`: Request processing middleware
- `api/auth/`: Authentication and authorization

## Installation

### System Requirements

**Minimum:**
- Python 3.10+
- 4GB RAM
- 2 CPU cores
- PostgreSQL 13+ (optional, for persistence)

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

# Start application
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Or use the Python module
python -m uvicorn api.main:app --reload
```

API available at `http://localhost:8000` with OpenAPI documentation at `/docs`

## Configuration

### Environment Configuration

```bash
# LLM Provider (for LLM-based rules)
GROQ_API_KEY=your_key_here                    # Recommended - free tier available
OLLAMA_BASE_URL=http://localhost:11434        # Air-gapped deployments

# Security
JWT_SECRET_KEY=your_secure_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database (optional)
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

### Policy Definition

Configure enforcement policies by adjusting severity thresholds and action mappings in `enforcement/verdict_adapter.py`:

```python
# Example: Customize severity-to-action mapping
class VerdictAdapter:
    @staticmethod
    def resolve_action(verdict):
        if verdict.severity in ["CRITICAL", "HIGH"]:
            return EnforcementAction.BLOCK
        elif verdict.severity == "MEDIUM":
            return EnforcementAction.WARN
        return EnforcementAction.ALLOW
```

## API Reference

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "tier_distribution": {
    "tier1": 85.2,
    "tier2": 12.8,
    "tier3": 2.0
  },
  "health_message": "All systems operational"
}
```

### Detection Endpoint

```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{
    "llm_response": "LLM generated output to validate",
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
  "method": "semantic_analysis",
  "confidence": 0.89,
  "processing_time_ms": 247.3,
  "failure_class": "hallucination",
  "severity": "high",
  "explanation": "Potential fabricated medical claim detected - requires verification",
  "blocked": true
}
```

### Batch Detection

```bash
curl -X POST http://localhost:8000/detect/batch \
  -H "Content-Type: application/json" \
  -d '[
    {"llm_response": "Response 1", "context": {}},
    {"llm_response": "Response 2", "context": {}}
  ]'
```

### Metrics

```bash
curl http://localhost:8000/metrics/stats
```

**Response:**
```json
{
  "total_detections": 15420,
  "tier1_count": 13140,
  "tier2_count": 1974,
  "tier3_count": 306,
  "distribution": {
    "tier1": 85.2,
    "tier2": 12.8,
    "tier3": 2.0
  },
  "health": {
    "is_healthy": true,
    "message": "All systems operational"
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
- PostgreSQL with persistent volumes (optional)
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
- ConfigMap-based configuration
- Ingress configuration included

## Monitoring & Observability

### Prometheus Metrics

Exposed at `/metrics` endpoint:

- `llm_obs_detections_total` - Total detections by action and method
- `llm_obs_processing_time_seconds` - Response time histogram
- `llm_obs_signal_execution_time` - Per-signal performance
- `llm_obs_rule_evaluation_time` - Rule evaluation latency
- `llm_obs_failures_total` - Detection failures by type

### Admin Dashboard

Streamlit-based management interface:

```bash
streamlit run dashboard/admin_dashboard.py --server.port 8501
```

Capabilities:
- Live detection monitoring
- Signal performance analysis
- Rule effectiveness tracking
- Historical analytics and reporting
- System health and diagnostics

## Understanding Observability vs Enforcement

**This is an observability system first, enforcement tool second:**

### Observability Features
- **Signal Extraction**: All signals are extracted and logged
- **Rule Evaluation**: Complete evaluation history
- **Verdict Tracking**: All verdicts recorded with reasoning
- **Metrics & Analytics**: Track patterns, trends, and model behavior
- **Audit Trail**: Complete history for compliance review

### Enforcement Options (Configurable)
- **Block**: Prevent high-risk outputs from delivery (optional)
- **Warn**: Flag concerns but allow delivery with context
- **Allow**: Permit with logging for later review

The system can operate in pure observability mode (log-only) or with active enforcement based on your risk tolerance and deployment needs.

## Security Considerations

### Input Validation
- Maximum input length: 50,000 characters
- Null byte and control character filtering
- Whitespace normalization
- Character encoding validation

### Attack Prevention
- Pattern-based attack detection (SQL injection, XSS, path traversal)
- Request timeout: 15 seconds with resource cleanup
- Rate limiting via middleware (configurable)
- Pathological input early rejection

### Data Protection
- JWT tokens with configurable expiration
- Bcrypt password hashing (if auth enabled)
- Parameterized queries via ORM
- Comprehensive audit logging

## Testing

### Test Suite

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Specific test categories
pytest tests/test_api.py              # API endpoints
pytest tests/test_signals.py          # Signal extraction
pytest tests/test_rules.py            # Rule evaluation
pytest tests/test_enforcement.py      # Enforcement logic
```

### Performance Benchmarks

```bash
# Load testing
python scripts/testing/load_test.py --requests 1000 --concurrent 50

# Typical results (4 CPU cores):
# - Throughput: ~800-1000 req/min
# - P95 latency: ~500ms
# - P99 latency: ~1200ms
```

## Use Cases

### Healthcare AI Assistant
```python
from enforcement.control_tower_v3 import ControlTowerV3

tower = ControlTowerV3()
result = tower.evaluate_response(
    llm_response="Aspirin cures cancer with 100% success rate",
    context={"domain": "healthcare", "high_risk": True}
)
# Result: action=BLOCK, severity=CRITICAL, failure_class=hallucination
```

### Financial Services
```python
result = tower.evaluate_response(
    llm_response="This stock will definitely increase 500% next week",
    context={"domain": "finance", "regulated": True}
)
# Result: action=BLOCK, severity=HIGH, failure_class=overconfidence
```

### Legal Document Generation
```python
result = tower.evaluate_response(
    llm_response="According to Brown v. Board of Education (1856)...",
    context={"domain": "legal", "requires_citations": True}
)
# Result: action=BLOCK, severity=HIGH, failure_class=fabrication
```

## Extending the System

### Adding Custom Signals

```python
# signals/custom/my_signal.py
from signals.base import BaseSignal

class MyCustomSignal(BaseSignal):
    def extract(self, prompt: str, response: str, metadata: dict) -> dict:
        # Your detection logic
        return {
            "signal": "my_custom_signal",
            "detected": True,
            "confidence": 0.85,
            "metadata": {"reason": "Custom detection triggered"}
        }

# Register in signals/registry.py
from .custom.my_signal import MyCustomSignal
ALL_SIGNALS.append(MyCustomSignal())
```

### Adding Custom Rules

```python
# rules/custom_rules.py
from rules.base import BaseRule
from rules.verdicts import Verdict

class MyCustomRule(BaseRule):
    def evaluate(self, signals: dict) -> Verdict | None:
        if signals.get("my_custom_signal", {}).get("detected"):
            return Verdict(
                severity="HIGH",
                failure_class="custom_failure",
                explanation="Custom rule triggered",
                confidence=0.85
            )
        return None

# Register in rules/engine.py
from rules.custom_rules import MyCustomRule
ALL_RULES.append(MyCustomRule())
```

## Performance Optimization

### Signal Execution
- Signals run in parallel for optimal performance
- Lightweight signals (regex) execute first
- Heavy signals (embeddings, LLM) are cached
- Failed signals don't block pipeline execution

### Caching Strategy
- Embedding vectors cached for 1 hour
- LLM-based rule results cached for similar inputs
- Redis integration available for distributed deployments

### Scaling Recommendations
- **<1K req/min**: Single instance (4 cores, 8GB RAM)
- **1-10K req/min**: 3-5 instances with load balancer
- **>10K req/min**: Kubernetes auto-scaling (10+ pods)

## Roadmap

- **Q2 2026**: Enhanced signal library (toxicity, bias detection)
- **Q3 2026**: Multi-language support (Spanish, French, German)
- **Q4 2026**: AutoML for custom signal/rule training
- **2027**: Real-time feedback loop for model improvement

## Support

- **Documentation**: Additional guides available in `/docs`
- **Community**: GitHub Issues for questions and bug reports
- **Contributing**: Pull requests welcome - see CONTRIBUTING.md

## License

MIT License - See [LICENSE](LICENSE) for full text.

## Standards Alignment

Development informed by:
- OWASP ASVS 4.0 (Input Validation, Error Handling)
- NIST Cybersecurity Framework
- ISO/IEC 27001 security controls
- GDPR Article 22 (Automated Decision Making)

## Important Disclaimers

**Detection Accuracy**: This system uses signal extraction, rule-based evaluation, and pattern matching to detect potential risks. Detection accuracy varies by content type and configuration. False positives and false negatives will occur.

**Not a Replacement for Human Review**: This tool is designed to augment, not replace, human oversight. Organizations must implement appropriate review processes for high-stakes decisions.

**Configuration Required**: Out-of-box detection policies are starting points. Tune signals, rules, and thresholds based on your specific use case, risk tolerance, and testing.

**Deployment Responsibility**: While the system includes security controls and follows best practices, deploying organizations are responsible for:
- Proper environment configuration and hardening
- Regular security updates and patches
- Appropriate access controls and monitoring
- Testing in their specific environment before production use
- Compliance with applicable regulations

**No Guarantees**: This software is provided "as is" per the MIT License. No warranties are made regarding detection accuracy, uptime, or suitability for any particular purpose.

---

**Status**: This software has been developed with production deployment in mind and includes comprehensive error handling, security controls, and monitoring. However, thorough evaluation and testing in your specific environment is essential before production use.
