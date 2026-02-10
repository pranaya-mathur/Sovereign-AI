#!/usr/bin/env python3
"""Test API with detailed timing breakdown to find the 2-second delay."""

import requests
import time
import json

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

print("\n" + "="*70)
print("  🔍 API Timing Breakdown Test")
print("="*70 + "\n")

# Step 1: Login
print("Step 1: Login...")
start = time.time()
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        params={"username": USERNAME, "password": PASSWORD},
        timeout=10
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    login_time = (time.time() - start) * 1000
    print(f"  ✅ Login successful in {login_time:.1f}ms\n")
except Exception as e:
    print(f"  ❌ Login failed: {e}\n")
    exit(1)

# Step 2: Test with timing breakdown
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

test_text = "SELECT * FROM users WHERE username='admin'--"

print("Step 2: Sending detection request...")
print(f"  Text: {test_text}\n")

# Measure total time
total_start = time.time()

try:
    # Send request
    request_start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/detect",
        headers=headers,
        json={"text": test_text},
        timeout=10
    )
    request_end = time.time()
    
    # Parse response
    parse_start = time.time()
    result = response.json()
    parse_end = time.time()
    
    total_time = (request_end - total_start) * 1000
    request_time = (request_end - request_start) * 1000
    parse_time = (parse_end - parse_start) * 1000
    
    print(f"Response received!\n")
    print(f"Timing Breakdown:")
    print(f"  Total time:          {total_time:.1f}ms")
    print(f"  Request time:        {request_time:.1f}ms")
    print(f"  Parse time:          {parse_time:.1f}ms")
    print(f"  Backend reports:     {result.get('processing_time_ms', 0):.1f}ms")
    print(f"  Unaccounted time:    {total_time - result.get('processing_time_ms', 0):.1f}ms")
    print()
    print(f"Result:")
    print(f"  Action:      {result.get('action')}")
    print(f"  Tier:        {result.get('tier_used')}")
    print(f"  Method:      {result.get('method')}")
    print(f"  Confidence:  {result.get('confidence')}")
    print(f"  Reason:      {result.get('reason')}")
    print()
    
    # Analysis
    backend_time = result.get('processing_time_ms', 0)
    overhead = total_time - backend_time
    
    print("Analysis:")
    if backend_time < 100:
        print(f"  ✅ Backend processing is FAST ({backend_time:.1f}ms)")
    else:
        print(f"  ⚠️  Backend processing is SLOW ({backend_time:.1f}ms)")
    
    if overhead > 1000:
        print(f"  ❌ HTTP/Network overhead is HUGE ({overhead:.1f}ms)")
        print(f"     This suggests:")
        print(f"     - Rate limiting delay?")
        print(f"     - Database connection slow?")
        print(f"     - Middleware processing?")
        print(f"     - Network latency?")
    elif overhead > 100:
        print(f"  ⚠️  HTTP overhead is elevated ({overhead:.1f}ms)")
    else:
        print(f"  ✅ HTTP overhead is normal ({overhead:.1f}ms)")
    
except requests.exceptions.Timeout:
    print(f"  ❌ Request timed out after 10 seconds")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("\nConclusion:")
print("If 'Unaccounted time' is >1000ms, the delay is NOT in detection logic.")
print("It's in: rate limiting, database, middleware, or network.")
print("="*70 + "\n")
