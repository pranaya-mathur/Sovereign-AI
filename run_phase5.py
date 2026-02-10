#!/usr/bin/env python3
"""Run Phase 5 API server.

Usage:
    python run_phase5.py
"""

import sys
import os

# Ensure we're in the project root
if not os.path.exists('api/app_complete.py'):
    print("❌ Error: Must run from project root directory")
    print("Current directory:", os.getcwd())
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Phase 5 API Server...")
    print("📊 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("\nℹ️  Default credentials:")
    print("   Admin: admin / admin123")
    print("   User:  testuser / test123")
    print("\n⏸️  Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "api.app_complete:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
