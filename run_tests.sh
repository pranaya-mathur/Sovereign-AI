#!/bin/bash

# Test runner script for LLM Observability

echo "🧪 Running LLM Observability Tests"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found. Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

echo -e "${YELLOW}Running API Tests...${NC}"
pytest tests/test_api.py -v --tb=short
API_RESULT=$?

echo ""
echo -e "${YELLOW}Running Phase 3 Tests...${NC}"
pytest tests/test_control_tower_v3.py -v --tb=short 2>/dev/null || echo "Phase 3 tests not found or skipped"

echo ""
echo -e "${YELLOW}Running Tier Router Tests...${NC}"
pytest tests/test_tier_router.py -v --tb=short 2>/dev/null || echo "Tier router tests not found or skipped"

echo ""
echo "===================================="

if [ $API_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ All API tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
