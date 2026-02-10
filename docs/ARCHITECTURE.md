# Architecture Overview

This document describes the high-level architecture and design decisions for the LLM Observability platform.

## System Components

### 1. Detection Pipeline

The detection pipeline uses a three-tier cascading approach to balance performance with accuracy:

#### Tier 1: Pattern Matching
- **Technology**: Regular expressions
- **Speed**: Sub-millisecond
- **Purpose**: Catch obvious violations with known patterns
- **Examples**: Specific hallucinated terms, clear prompt injection attempts

#### Tier 2: Semantic Analysis
- **Technology**: Sentence transformers (embeddings)
- **Speed**: 5-10ms
- **Purpose**: Handle ambiguous cases requiring semantic understanding
- **Examples**: Paraphrased violations, contextual issues

#### Tier 3: LLM Reasoning
- **Technology**: LLM agents (Groq/Ollama)
- **Speed**: 50-100ms (or 0.1ms with cache)
- **Purpose**: Complex cases requiring deep reasoning
- **Examples**: Sophisticated prompt engineering, context-dependent violations

### 2. Policy Engine

The policy engine enforces configurable rules based on detected violations:

```
Detection → Policy Lookup → Action (BLOCK/WARN/ALLOW)
```

- Policies defined in YAML (`config/policy.yaml`)
- Each failure class maps to severity level and action
- Supports custom policies without code changes

### 3. Caching Layer

Decision caching ensures deterministic behavior:

- LRU cache for detection results
- Cache keys based on input hash
- Significantly reduces latency for repeated queries
- Target cache hit rate: >95%

## Data Flow

```
User Input
    ↓
Input Validation
    ↓
Tier Router
    ├→ Tier 1 (fast path) → Policy Engine
    ├→ Tier 2 (semantic) → Policy Engine  
    └→ Tier 3 (LLM) → Policy Engine
                ↓
          Decision Cache
                ↓
        Action Execution
                ↓
           User Response
```

## Design Decisions

### Why Three Tiers?

Single-tier approaches have tradeoffs:
- **Regex only**: Fast but limited accuracy
- **LLM only**: Accurate but slow and expensive
- **Embeddings only**: Good middle ground but not perfect

Three tiers let us route intelligently:
- Common cases go through fast path
- Ambiguous cases get semantic analysis
- Edge cases get full LLM reasoning

### Why Cascading vs Parallel?

We use cascading (sequential) evaluation rather than running all tiers in parallel because:
- Most cases are caught in Tier 1 (95%+)
- No need to waste resources on higher tiers
- Reduces overall latency
- Lowers API costs for LLM tier

### Why YAML for Policies?

YAML configuration allows:
- Non-engineers to update policies
- Version control of policy changes
- Easy A/B testing of different policies
- No code deployments for policy updates

## Scaling Considerations

### Horizontal Scaling

The system is designed to scale horizontally:
- Stateless API servers
- Shared cache layer (Redis)
- Database connection pooling
- Load balancer compatible

### Performance Optimization

- Input validation happens before expensive operations
- Early returns for obvious cases
- Batch processing support for multiple inputs
- Async processing for non-blocking operations

### Resource Management

- Timeout protection prevents hanging requests
- Rate limiting prevents abuse
- Circuit breakers for external dependencies
- Graceful degradation when services unavailable

## Security Architecture

### Input Sanitization

- Length limits on all inputs
- Character validation
- Protection against injection attacks
- Timeout on regex operations

### Authentication & Authorization

- API key-based auth
- Role-based access control
- Rate limiting per user
- Audit logging

### Data Privacy

- No persistent storage of user inputs by default
- Optional anonymization of logs
- Compliance with data retention policies

## Monitoring & Observability

### Metrics Collected

- Request latency (p50, p95, p99)
- Detection tier distribution
- Cache hit rates
- Error rates by type
- Throughput (requests/second)

### Logging

- Structured JSON logs
- Request tracing IDs
- Error context and stack traces
- Performance breakdowns

### Alerts

- High error rate
- Slow response times
- Cache performance degradation
- Abnormal tier distribution

## Future Enhancements

### Short Term

- Redis caching layer
- Prometheus metrics
- Grafana dashboards
- Kubernetes deployment

### Medium Term

- A/B testing framework
- Auto-tuning of thresholds
- Multi-language support
- Custom detector plugins

### Long Term

- Federated learning for privacy
- Active learning for pattern updates
- Real-time threat intelligence
- Anomaly detection

## Technology Stack

- **Language**: Python 3.10+
- **Web Framework**: FastAPI
- **Embeddings**: sentence-transformers
- **LLM**: Groq/Ollama
- **Caching**: functools.lru_cache (Redis planned)
- **Database**: PostgreSQL (SQLite for dev)
- **Deployment**: Docker, Kubernetes

## References

- [Defense in Depth Security](https://en.wikipedia.org/wiki/Defense_in_depth_(computing))
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [LangGraph](https://python.langchain.com/docs/langgraph)
