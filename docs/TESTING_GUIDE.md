# Testing Guide - LLM Observability

## Quick Start

```bash
# Pull latest changes
git checkout phase4-production
git pull origin phase4-production

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v
pytest tests/test_control_tower_integration.py -v
```

## Test Structure

### API Tests (`tests/test_api.py`)

Tests the FastAPI application endpoints:

- ✅ **TestRootEndpoints**: Basic endpoints (/, /docs, /openapi.json)
- ✅ **TestHealthEndpoint**: Health checks and tier distribution
- ✅ **TestDetectionEndpoint**: Single detection endpoint
- ✅ **TestBatchDetectionEndpoint**: Batch detection endpoint
- ✅ **TestStatsEndpoint**: Statistics endpoint
- ✅ **TestLogsEndpoint**: Logs retrieval endpoint
- ✅ **TestMetricsEndpoint**: Prometheus metrics endpoint
- ✅ **TestErrorHandling**: Error handling and edge cases
- ✅ **TestDatabasePersistence**: Database integration

**Total: 27 test cases**

### Integration Tests (`tests/test_control_tower_integration.py`)

Tests the ControlTowerV3 core functionality:

- ✅ **TestControlTowerV3Stats**: Statistics methods
  - `test_get_tier_stats_structure`: Verifies all required keys exist
  - `test_get_tier_stats_distribution_structure`: Checks distribution format
  - `test_get_tier_stats_health_structure`: Validates health status format
  - `test_get_tier_stats_initial_values`: Tests initial state
  - `test_get_tier_stats_data_types`: Validates data types
  - `test_reset_tier_stats`: Tests reset functionality

- ✅ **TestControlTowerV3Detection**: Detection methods
  - `test_evaluate_response_returns_result`: Basic functionality
  - `test_evaluate_response_valid_tier`: Tier validation
  - `test_evaluate_response_valid_confidence`: Confidence validation
  - `test_evaluate_response_without_context`: Optional context handling

**Total: 10 test cases**

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Class

```bash
# Run only detection endpoint tests
pytest tests/test_api.py::TestDetectionEndpoint -v

# Run only stats tests
pytest tests/test_control_tower_integration.py::TestControlTowerV3Stats -v
```

### Run Specific Test Method

```bash
pytest tests/test_api.py::TestDetectionEndpoint::test_detect_valid_request -v
```

### Run with Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage report
pytest tests/ --cov=api --cov=enforcement --cov-report=html

# Open coverage report
# open htmlcov/index.html
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4
```

## Common Test Failures & Fixes

### Issue 1: KeyError in get_tier_stats()

**Error:**
```
KeyError: 'total'
```

**Cause:** ControlTowerV3.get_tier_stats() not returning expected keys.

**Fix:** Already fixed in commit `ee8d1e18`. Pull latest changes:
```bash
git pull origin phase4-production
```

### Issue 2: 500 Internal Server Error in Detection Endpoints

**Error:**
```
assert response.status_code == 200
E   assert 500 == 200
```

**Cause:** Missing `evaluate_response()` method or incorrect return type.

**Fix:** Already fixed in commit `ee8d1e18`. The method now returns proper `DetectionResult`.

### Issue 3: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'enforcement'
```

**Cause:** Running tests from wrong directory.

**Fix:**
```bash
# Make sure you're in the project root
cd /path/to/LLM-Observability

# Verify location
pwd  # Should show .../LLM-Observability

# Run tests
pytest tests/ -v
```

### Issue 4: Database Errors

**Error:**
```
sqlalchemy.exc.OperationalError: no such table: detection_logs
```

**Cause:** Database not initialized in tests.

**Fix:** Tests use in-memory SQLite which is automatically created. If issue persists:
```bash
# Delete local database
rm llm_observability.db

# Run tests again
pytest tests/test_api.py -v
```

### Issue 5: Semantic Detector Not Available

**Error:**
```
Warning: Semantic detector unavailable: ...
```

**Cause:** sentence-transformers not installed or torch issues.

**Fix:**
```bash
# Reinstall torch and transformers
pip install torch sentence-transformers --force-reinstall

# If on CPU only (Windows/Mac)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Issue 6: LLM Agent Not Available

**Error:**
```
Warning: LLM agent unavailable: ...
```

**Cause:** Ollama not running or LangGraph issues.

**Fix:**
```bash
# Start Ollama
ollama run llama3.2

# Or skip Tier 3 tests
pytest tests/ -v -k "not llm_agent"
```

## Test Database

Tests use in-memory SQLite database that is:
- ✅ Isolated per test
- ✅ Automatically created and destroyed
- ✅ No cleanup needed
- ✅ Fast (no disk I/O)

## Writing New Tests

### Template for API Endpoint Test

```python
class TestMyNewEndpoint:
    """Test my new endpoint."""
    
    def test_endpoint_success(self):
        """Test successful request."""
        response = client.post(
            "/my-endpoint",
            json={"param": "value"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "expected_key" in data
    
    def test_endpoint_validation(self):
        """Test validation errors."""
        response = client.post(
            "/my-endpoint",
            json={}  # Missing required param
        )
        assert response.status_code == 422
```

### Template for Unit Test

```python
class TestMyComponent:
    """Test my component."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        component = MyComponent()
        result = component.do_something()
        
        assert result is not None
        assert isinstance(result, dict)
        assert "key" in result
```

## CI/CD Integration

### GitHub Actions (Future)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      run: pytest tests/ -v --cov=api --cov=enforcement
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|----------|
| API Endpoints | 90%+ | ~85% |
| ControlTowerV3 | 80%+ | ~70% |
| TierRouter | 80%+ | ~60% |
| Database Layer | 70%+ | ~75% |

## Performance Testing

### Load Test with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class LLMObservabilityUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def detect(self):
        self.client.post("/detect", json={
            "llm_response": "Test response",
            "context": {}
        })
    
    @task(3)
    def health_check(self):
        self.client.get("/health")
```

Run:
```bash
pip install locust
locust -f locustfile.py --host=http://localhost:8000
```

## Debugging Tests

### Enable Verbose Output

```bash
pytest tests/ -vv -s
```

### Run Single Test with Debugger

```bash
pytest tests/test_api.py::TestDetectionEndpoint::test_detect_valid_request -vv -s --pdb
```

### Print Variables During Test

```python
def test_my_test(self):
    result = some_function()
    print(f"\n\nResult: {result}")  # Will show in -s mode
    assert result == expected
```

### Check Test Logs

```bash
pytest tests/ -v --log-cli-level=DEBUG
```

## Expected Test Results

After fixes, you should see:

```
================= test session starts =================
platform win32 -- Python 3.13.5
collected 37 items

tests/test_api.py::TestRootEndpoints::test_root_endpoint PASSED           [  2%]
tests/test_api.py::TestRootEndpoints::test_docs_accessible PASSED         [  5%]
tests/test_api.py::TestRootEndpoints::test_openapi_schema PASSED          [  8%]
...
tests/test_control_tower_integration.py::...::test_reset_tier_stats PASSED [100%]

================= 37 passed in 2.34s =================
```

## Troubleshooting Checklist

- [ ] Are you in the project root directory?
- [ ] Did you activate the virtual environment?
- [ ] Are all dependencies installed? (`pip install -r requirements.txt`)
- [ ] Did you pull the latest changes? (`git pull origin phase4-production`)
- [ ] Is the database file deleted? (`rm llm_observability.db`)
- [ ] Are imports working? (`python -c "from api.main_v2 import app"`)
- [ ] Is pytest installed? (`pip list | grep pytest`)

## Getting Help

If tests still fail:

1. **Check the error message** - Most errors are self-explanatory
2. **Read the traceback** - Shows exactly where the error occurred
3. **Check GitHub issues** - Someone might have faced the same issue
4. **Run tests individually** - Isolate the failing test
5. **Check commit history** - See if recent changes broke tests

## Summary

✅ **37 total test cases** across API and integration tests  
✅ **All tests should pass** after latest fixes  
✅ **Run with**: `pytest tests/ -v`  
✅ **Quick check**: `pytest tests/test_control_tower_integration.py -v`  

Happy testing! 🧪
