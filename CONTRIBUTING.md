# Contributing to Sovereign AI

First off, thank you for considering contributing to Sovereign AI! Our goal is to build the most robust, fully-sovereign telemetry and enforcement layer for enterprise LLMs.

To maintain our "MVP-Ready" enterprise status, we have strict guidelines for contributions. Please review them before opening a Pull Request.

## 1. Local Development Setup

We use standard Python packaging to make local development painless.

```bash
# Clone the repo
git clone https://github.com/pranaya-mathur/Sovereign-AI.git
cd Sovereign-AI

# Install in editable mode
pip install -e .

# Setup your local policy configuration
cp config/policy.example.yaml config/policy.yaml
```

## 2. Architectural Philosophy

If you are contributing a new feature, please ensure it aligns with the core architecture:
- **Zero Network Trust:** All Tier 1 and Tier 2 rules must execute locally on the host machine. Do not introduce external API dependencies into these critical paths.
- **Fail-open (Usually):** Unless a timeout or exception occurs within a `Critical` or `High` severity block, the system should allow the response rather than completely blocking the application.
- **Observability First:** All new rules, embeddings, and agents must trace their steps using OpenTelemetry. Utilize the `ControlTowerV3.tracer.start_as_current_span()` context manager.

## 3. Pull Request Guidelines

Before submitting a Pull Request, you must verify your changes against our test suite.

### Running Tests
Sovereign AI currently maintains a 100% pass rate (74/74 tests) on the main branch. We do not merge broken code.

```bash
# Run the full suite
pytest tests/ -v

# Run just the embedding tests if you manipulated signals/
pytest tests/test_semantic_detector.py -v
```

### PR Formatting
Please prefix your PR titles using standard conventional commits:
- `feat:` for new capabilities.
- `fix:` for bug fixes.
- `docs:` for README and walkthrough updates.
- `chore:` for dependency updates or CI/CD adjustments.

## 4. Hardware Support

If you are modifying embedding models or PyTorch logic inside the `signals/` directory, your code MUST support fallback loops. Rely on the `policy_loader.py` `get_hardware_config()` method to dynamically target `cpu`, `cuda`, or `mps`. Hardcoding `.to('cuda')` will be rejected as it breaks MacOS usage.
