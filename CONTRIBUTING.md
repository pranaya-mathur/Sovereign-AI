# Contributing to LLM Observability

Thank you for considering contributing to this project. This document outlines the process and guidelines for contributions.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/LLM-Observability.git
   cd LLM-Observability
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-detector` for new features
- `fix/regex-timeout` for bug fixes
- `docs/api-examples` for documentation

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Keep functions focused and under 50 lines when possible
- Add docstrings for public methods

### Testing

Run tests before submitting:
```bash
pytest tests/
```

Add tests for new features:
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Maintain test coverage above 70%

## Adding New Detection Patterns

### 1. Define the Failure Class

Add to `contracts/failure_classes.py`:
```python
class FailureClass(str, Enum):
    # ... existing classes
    NEW_PATTERN = "new_pattern"
```

### 2. Add Detection Logic

For Tier 1 (regex), add patterns in the appropriate detector.

For Tier 2 (semantic), add example patterns in `signals/embeddings/semantic_detector.py`:
```python
self.failure_patterns = {
    "new_pattern": [
        "example text that represents this pattern",
        "another example"
    ]
}
```

### 3. Configure Policy

Add to `config/policy.yaml`:
```yaml
failure_policies:
  new_pattern:
    severity: "high"
    action: "warn"
    reason: "Description of why this is flagged"
```

### 4. Add Tests

Create test cases in `tests/`:
```python
def test_new_pattern_detection():
    detector = YourDetector()
    result = detector.detect("test input")
    assert result.detected == True
```

## Pull Request Process

1. Update documentation for any changed functionality
2. Add entries to CHANGELOG.md under [Unreleased]
3. Ensure all tests pass
4. Update README.md if adding major features
5. Submit PR with clear description of changes

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested the changes

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Code Review

All submissions require review. Expect feedback on:
- Code quality and style
- Test coverage
- Performance implications
- Security considerations

## Issue Reporting

When reporting issues, include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs

## Questions?

Open an issue with the "question" label or start a discussion.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
