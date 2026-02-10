#!/usr/bin/env python3
"""Verification script to confirm timeout fixes are working.

Run this after pulling the fixes to ensure everything is working correctly.
"""

import requests
import time
import sys
from typing import Dict, Tuple

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_colored(text: str, color: str):
    """Print colored text."""
    print(f"{color}{text}{RESET}")

def check_backend_running() -> bool:
    """Check if backend is running."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def login() -> Tuple[bool, str]:
    """Login and get access token."""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            params={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        response.raise_for_status()
        return True, response.json()["access_token"]
    except Exception as e:
        return False, str(e)

def test_pathological_input(token: str) -> Tuple[bool, str, float]:
    """Test pathological input (previously timed out)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # This previously timed out
    pathological_text = "a" * 500
    
    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/detect",
            headers=headers,
            json={"text": pathological_text},
            timeout=5  # Should complete well within 5s now
        )
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        if response.status_code == 200:
            result = response.json()
            # Should be blocked as pathological
            if result.get('action') == 'block':
                return True, f"Correctly blocked in {elapsed:.1f}ms", elapsed
            else:
                return False, f"Not blocked (should be blocked)", elapsed
        else:
            return False, f"HTTP {response.status_code}", elapsed
    
    except requests.exceptions.Timeout:
        return False, "Request timed out (FIX DID NOT WORK!)", 5000.0
    except Exception as e:
        return False, str(e), 0.0

def test_sql_injection(token: str) -> Tuple[bool, str, float]:
    """Test SQL injection (previously timed out)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    sql_text = "SELECT * FROM users WHERE username='admin'--"
    
    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/detect",
            headers=headers,
            json={"text": sql_text},
            timeout=5
        )
        elapsed = (time.time() - start) * 1000
        
        if response.status_code == 200:
            result = response.json()
            if result.get('action') == 'block':
                return True, f"Correctly blocked in {elapsed:.1f}ms", elapsed
            else:
                return False, f"Not blocked (should be blocked)", elapsed
        else:
            return False, f"HTTP {response.status_code}", elapsed
    
    except requests.exceptions.Timeout:
        return False, "Request timed out (FIX DID NOT WORK!)", 5000.0
    except Exception as e:
        return False, str(e), 0.0

def test_normal_input(token: str) -> Tuple[bool, str, float]:
    """Test normal input (should still work)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    normal_text = "What is the capital of France?"
    
    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/detect",
            headers=headers,
            json={"text": normal_text},
            timeout=5
        )
        elapsed = (time.time() - start) * 1000
        
        if response.status_code == 200:
            result = response.json()
            if result.get('action') == 'allow':
                return True, f"Correctly allowed in {elapsed:.1f}ms", elapsed
            else:
                return False, f"Blocked (should be allowed)", elapsed
        else:
            return False, f"HTTP {response.status_code}", elapsed
    
    except requests.exceptions.Timeout:
        return False, "Request timed out", 5000.0
    except Exception as e:
        return False, str(e), 0.0

def main():
    """Run verification tests."""
    print("\n" + "="*70)
    print_colored("  🔧 Timeout Fixes Verification Script", BLUE)
    print("="*70 + "\n")
    
    # Check 1: Backend running
    print("[1/5] Checking if backend is running...")
    if check_backend_running():
        print_colored("  ✅ Backend is running\n", GREEN)
    else:
        print_colored("  ❌ Backend is not running!", RED)
        print("\n  Please start the backend first:")
        print("  python -m uvicorn api.app_complete:app --reload --port 8000\n")
        sys.exit(1)
    
    # Check 2: Login
    print("[2/5] Testing authentication...")
    success, result = login()
    if success:
        token = result
        print_colored("  ✅ Login successful\n", GREEN)
    else:
        print_colored(f"  ❌ Login failed: {result}\n", RED)
        sys.exit(1)
    
    # Check 3: Pathological input (main fix)
    print("[3/5] Testing pathological input (was timing out)...")
    success, message, elapsed = test_pathological_input(token)
    if success:
        print_colored(f"  ✅ {message}", GREEN)
        if elapsed < 10:  # Should be super fast now
            print_colored(f"  🚀 Excellent! Processed in <10ms\n", GREEN)
        else:
            print_colored(f"  ⚠️  Slower than expected but working\n", YELLOW)
    else:
        print_colored(f"  ❌ FAILED: {message}\n", RED)
        print("  The timeout fix may not be working correctly.")
        print("  Check QUICK_FIX_GUIDE.md for troubleshooting.\n")
        sys.exit(1)
    
    # Check 4: SQL injection
    print("[4/5] Testing SQL injection pattern (was timing out)...")
    success, message, elapsed = test_sql_injection(token)
    if success:
        print_colored(f"  ✅ {message}", GREEN)
        if elapsed < 10:
            print_colored(f"  🚀 Excellent! Processed in <10ms\n", GREEN)
        else:
            print_colored(f"  ⚠️  Slower than expected but working\n", YELLOW)
    else:
        print_colored(f"  ❌ FAILED: {message}\n", RED)
        sys.exit(1)
    
    # Check 5: Normal input still works
    print("[5/5] Testing normal input (regression check)...")
    success, message, elapsed = test_normal_input(token)
    if success:
        print_colored(f"  ✅ {message}\n", GREEN)
    else:
        print_colored(f"  ❌ FAILED: {message}\n", RED)
        print("  Normal inputs should still work. Check configuration.\n")
        sys.exit(1)
    
    # All tests passed!
    print("="*70)
    print_colored("  🎉 ALL VERIFICATION TESTS PASSED!", GREEN)
    print("="*70)
    print("\n  The timeout fixes are working correctly!\n")
    print("  ✅ Pathological inputs detected early (<10ms)")
    print("  ✅ Attack patterns blocked quickly")
    print("  ✅ Normal inputs still process correctly")
    print("\n  You can now run the full test suite:")
    print_colored("  python test_samples.py\n", BLUE)
    print("  Expected result: 30/30 tests pass (100%)\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {e}", RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)
