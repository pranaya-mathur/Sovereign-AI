# Files to Clean Up

These files should be deleted to make the repo cleaner:

## Root Directory Cleanup

```bash
# Debug/diagnostic scripts - move to scripts/ or delete
rm debug_api.py
rm diagnostic_full_trace.py  
rm restart_backend.py
rm verify_fixes.py

# Test files in root - move to tests/ or delete
rm test_api_timing.py
rm test_pathological_direct.py
rm test_samples.py
rm test_samples.bat

# Phase-specific files - delete
rm run_phase5.py
rm run_phase5.sh
rm start_phase5.sh
rm stop_phase5.sh

# Redundant requirements files - keep only requirements.txt
rm requirements-phase5.txt
rm requirements_phase5.txt

# Redundant documentation - already consolidated
rm QUICKSTART_PHASE1.md
rm QUICK_FIX_GUIDE.md  
rm TESTING.md
rm TESTING_GUIDE.md
rm TODO.md  # replaced by TODO.txt

# Cleanup marker
rm .cleanup_marker
```

## After Cleanup

The root directory should only have:
- README.md
- CHANGELOG.md
- CONTRIBUTING.md
- LICENSE
- NOTES.md
- TODO.txt
- QUICKSTART.md (keep this one)
- requirements.txt
- docker-compose.yml
- Dockerfile
- pytest.ini
- alembic.ini
- .env.example
- .gitignore
- .dockerignore
- .gitattributes
- run_tests.sh

## Delete docs/ARCHITECTURE.md too

It's too polished and formal. Real side projects don't have that level of documentation initially.

```bash
rm docs/ARCHITECTURE.md
```

This file itself should also be deleted after cleanup is done.
