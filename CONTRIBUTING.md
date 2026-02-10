# Contributing to LLM Observability

Thanks for your interest in contributing. This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your changes
4. Make your changes
5. Run tests to ensure everything works
6. Submit a pull request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/LLM-Observability.git
cd LLM-Observability

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and relatively short

## Adding New Detection Patterns

To add a new failure detection class:

1. **Define the failure class** in `contracts/failure_classes.py`:

```python
class FailureClass(str, Enum):
    # ... existing classes
    YOUR_NEW_CLASS = "your_new_class"
```

2. **Add detection logic** in the appropriate tier:
   - Tier 1: Add regex pattern in `enforcement/control_tower_v3.py`
   - Tier 2: Add semantic patterns in `signals/embeddings/semantic_detector.py`
   - Tier 3: Update LLM agent logic if needed

3. **Configure policy** in `config/policy.yaml`:

```yaml
failure_policies:
  your_new_class:
    severity: "high"
    action: "warn"
    reason: "Description of why this is problematic"
```

4. **Add tests** in `tests/test_detection.py`:

```python
def test_your_new_class():
    result = control_tower.detect("test input")
    assert result.failure_class == FailureClass.YOUR_NEW_CLASS
```

## Testing

Before submitting a PR:

- Run all tests: `pytest tests/`
- Test manually with example scripts
- Verify no regressions in existing functionality

## Pull Request Process

1. Update documentation if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Write a clear PR description explaining:
   - What problem does this solve?
   - What changes were made?
   - How was it tested?
5. Reference any related issues

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add new detection pattern for X`
- `fix: resolve timeout in semantic detector`
- `docs: update installation instructions`
- `test: add tests for edge cases`
- `refactor: simplify routing logic`

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about usage
- Clarification on contribution process

## Code of Conduct

Be respectful and constructive in all interactions. We're all here to learn and build something useful together.
