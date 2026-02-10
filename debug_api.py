#!/usr/bin/env python3
"""Debug script to identify API errors."""

import requests
import json

BASE_URL = "http://localhost:8000"

print("🔍 Debugging API Errors\n")
print("="*60)

# 1. Login
print("\n1. Testing login...")
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        params={"username": "admin", "password": "admin123"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"   ✅ Token obtained: {token[:30]}...")
    else:
        print(f"   ❌ Error: {response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Exception: {e}")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. Test /api/auth/me
print("\n2. Testing /api/auth/me...")
try:
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"   ❌ Error response:")
        print(f"   {response.text}")
        try:
            error_detail = response.json()
            print(f"   Detail: {json.dumps(error_detail, indent=2)}")
        except:
            pass
except Exception as e:
    print(f"   ❌ Exception: {e}")

# 3. Test /api/admin/users
print("\n3. Testing /api/admin/users...")
try:
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        users = response.json()
        print(f"   ✅ Found {len(users)} users")
        for user in users:
            print(f"      - {user['username']} ({user['role']})")
    else:
        print(f"   ❌ Error response:")
        print(f"   {response.text}")
        try:
            error_detail = response.json()
            print(f"   Detail: {json.dumps(error_detail, indent=2)}")
        except:
            pass
except Exception as e:
    print(f"   ❌ Exception: {e}")

# 4. Test /api/detect
print("\n4. Testing /api/detect...")
try:
    response = requests.post(
        f"{BASE_URL}/api/detect",
        headers=headers,
        json={"text": "Test message"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Action: {result.get('action')}")
        print(f"   ✅ Tier: {result.get('tier_used')}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# 5. Test health check
print("\n5. Testing /api/monitoring/health...")
try:
    response = requests.get(f"{BASE_URL}/api/monitoring/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        health = response.json()
        print(f"   ✅ Status: {health.get('status')}")
        print(f"   ✅ Database: {health.get('database')}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

print("\n" + "="*60)
print("📝 Check the API console for detailed error stack traces")
print("="*60)
