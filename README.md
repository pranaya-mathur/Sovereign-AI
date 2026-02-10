# LLM Observability Platform

## Overview

An observability system for Large Language Models with multi-tier detection architecture. The system uses a cascading approach: fast regex patterns for common cases, semantic embeddings for ambiguous content, and LLM-based reasoning for complex edge cases.

### Key Features

- **Multi-Tier Detection**: Cascading detection system (regex → embeddings → LLM)
- **Policy-Driven Enforcement**: Configurable policies via YAML
- **Real-time Monitoring**: Track detection patterns and system health
- **Caching**: Deterministic decisions with high cache hit rates
- **Performance**: Sub-10ms average detection for most cases

## Architecture

```
LLM Response
     |
     v
Tier Router
     |
     +-- Tier 1: Regex Patterns (fast path)
     |
     +-- Tier 2: Semantic Embeddings (gray zone)
     |
     +-- Tier 3: LLM Agent (complex cases)
     |
     v
Policy Engine
     |
     v
BLOCK / WARN / ALLOW
```

### Detection Tiers

| Tier | Method | Typical Speed | Use Case |
|------|--------|---------------|----------|
| 1 | Regex Patterns | <1ms | Clear violations with known patterns |
| 2 | Semantic Embeddings | 5-10ms | Ambiguous content requiring similarity matching |
| 3 | LLM Agent | 50-100ms | Complex cases needing contextual reasoning |

## Prerequisites

- Python 3.10 or higher
- Ollama (optional, for Tier 3 detection)
- Groq API key (optional, for faster Tier 3)

## Installation

```bash
git clone https://github.com/pranaya-mathur/LLM-Observability.git
cd LLM-Observability

pip install -r requirements.txt

# Optional: Configure environment variables
cp .env.example .env
# Edit .env with your API keys if using Groq
```

## Quick Start

### Running the Demo

```bash
python -m examples.run_phase3_demo
```

### Using the API

```bash
# Start the server
python -m api.app

# In another terminal, test detection
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "Your test text here"}'
```

## Configuration

Edit `config/policy.yaml` to customize detection policies:

```yaml
failure_policies:
  fabricated_concept:
    severity: "critical"
    action: "block"
    reason: "Hallucinated content detected"
  
  missing_grounding:
    severity: "high"
    action: "warn"
    reason: "Claims lack proper citations"
```

### Threshold Configuration

Tier routing thresholds:
- Tier 1 high confidence: >= 0.8
- Tier 1 low confidence: <= 0.3
- Tier 2 range: 0.3-0.8
- Tier 3: < 0.3 or requires deeper analysis

## Project Structure

```
LLM-Observability/
├── config/              # Configuration files
│   ├── policy.yaml
│   └── policy_loader.py
├── contracts/           # Data contracts and enums
│   ├── failure_classes.py
│   └── severity_levels.py
├── enforcement/         # Detection and routing logic
│   ├── control_tower_v3.py
│   └── tier_router.py
├── signals/             # Detection modules
│   ├── embeddings/
│   └── grounding/
├── agent/               # LLM agent for complex cases
│   ├── langgraph_agent.py
│   ├── llm_providers.py
│   └── decision_cache.py
├── api/                 # REST API
├── examples/            # Example usage
└── tests/               # Test suite
```

## Development Status

### Completed

- Basic regex pattern detection
- Semantic embedding integration
- Multi-tier routing system
- Policy configuration system
- Basic API endpoints

### In Progress

- FastAPI production wrapper
- Structured logging
- Metrics dashboard
- Database persistence

### Planned

- Kubernetes deployment configs
- Distributed tracing
- A/B testing framework
- Performance profiling tools

## Performance Notes

Performance varies based on input and system configuration:

- Tier 1 typically handles 90%+ of cases
- Caching significantly improves repeated queries
- LLM tier requires local Ollama or API access
- Windows users may see slower embedding initialization

## Monitoring

Check system statistics:

```python
from enforcement.control_tower_v3 import ControlTowerV3

control_tower = ControlTowerV3()
stats = control_tower.get_tier_stats()
print(stats)
```

## Example Use Cases

### Detecting Hallucinations

```python
result = control_tower.detect("RAG stands for Random Access Grammar")
if result.action == "block":
    print(f"Blocked: {result.failure_class}")
```

### Checking Citations

```python
result = control_tower.detect("Studies show this is effective")
if result.action == "warn":
    print(f"Warning: {result.reason}")
```

## Contributing

Contributions welcome. To add new detection patterns:

1. Define the failure class in `contracts/failure_classes.py`
2. Add detection logic in appropriate tier module
3. Configure policy in `config/policy.yaml`
4. Add tests in `tests/`

See CONTRIBUTING.md for detailed guidelines.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with standard MLOps practices. Inspired by defense-in-depth security patterns.
