#!/bin/bash
# Phase 5 Quick Start Script
# Starts API and Dashboard together

set -e

echo "============================================================"
echo "          LLM Observability - Phase 5 Startup              "
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found${NC}"

# Check if pip packages are installed
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies not installed. Installing...${NC}"
    pip install -r requirements_phase5.txt
else
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# Create log directory
mkdir -p logs

# Start API server in background
echo ""
echo -e "${BLUE}🚀 Starting API Server on port 8000...${NC}"
python3 -m uvicorn api.app_complete:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✅ API Server started (PID: $API_PID)${NC}"

# Wait for API to be ready
echo -e "${BLUE}⏳ Waiting for API to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready!${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API failed to start. Check logs/api.log${NC}"
        exit 1
    fi
done

# Show API info
echo ""
echo -e "${GREEN}📊 API Information:${NC}"
echo "  - URL: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/api/monitoring/health"
echo "  - Logs: logs/api.log"

# Show default credentials
echo ""
echo -e "${GREEN}🔑 Default Credentials:${NC}"
echo "  Admin:"
echo "    - Username: admin"
echo "    - Password: admin123"
echo "  Test User:"
echo "    - Username: testuser"
echo "    - Password: test123"

# Start Dashboard in background
echo ""
echo -e "${BLUE}🎨 Starting Dashboard on port 8501...${NC}"
streamlit run dashboard/admin_dashboard.py > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo -e "${GREEN}✅ Dashboard started (PID: $DASHBOARD_PID)${NC}"

# Wait for Dashboard to be ready
echo -e "${BLUE}⏳ Waiting for Dashboard to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8501/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Dashboard is ready!${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Dashboard may take longer to start. Check logs/dashboard.log${NC}"
        break
    fi
done

# Show Dashboard info
echo ""
echo -e "${GREEN}🎨 Dashboard Information:${NC}"
echo "  - URL: http://localhost:8501"
echo "  - Logs: logs/dashboard.log"

# Save PIDs for shutdown
echo $API_PID > logs/api.pid
echo $DASHBOARD_PID > logs/dashboard.pid

echo ""
echo "============================================================"
echo -e "${GREEN}🎉 Phase 5 is now running!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:8501 in your browser"
echo "  2. Login with: admin / admin123"
echo "  3. Explore the dashboard features"
echo "  4. Test API at: http://localhost:8000/docs"
echo ""
echo "To stop everything:"
echo "  ./stop_phase5.sh"
echo ""
echo "To run automated tests:"
echo "  python scripts/test_phase5_complete.py"
echo ""
echo "View logs:"
echo "  tail -f logs/api.log"
echo "  tail -f logs/dashboard.log"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop...${NC}"
echo ""

# Wait for interrupt
trap "echo ''; echo -e '${YELLOW}Shutting down...${NC}'; kill $API_PID $DASHBOARD_PID 2>/dev/null; echo -e '${GREEN}✅ Stopped${NC}'; exit 0" INT TERM

# Keep script running
wait
