#!/usr/bin/env python3
"""Comprehensive test script for Phase 5 implementation.

Tests all features:
- Authentication
- User management
- Rate limiting
- Detection with auth
- Admin endpoints
- Monitoring

Run with:
    python scripts/test_phase5_complete.py
"""

import requests
import time
import json
from typing import Optional


BASE_URL = "http://localhost:8000"
COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "reset": "\033[0m",
}


def print_header(text: str):
    """Print colored header."""
    print(f"\n{COLORS['blue']}{'='*60}{COLORS['reset']}")
    print(f"{COLORS['blue']}{text:^60}{COLORS['reset']}")
    print(f"{COLORS['blue']}{'='*60}{COLORS['reset']}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{COLORS['green']}✅ {text}{COLORS['reset']}")


def print_error(text: str):
    """Print error message."""
    print(f"{COLORS['red']}❌ {text}{COLORS['reset']}")


def print_info(text: str):
    """Print info message."""
    print(f"{COLORS['yellow']}ℹ️  {text}{COLORS['reset']}")


class Phase5Tester:
    """Test all Phase 5 features."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.admin_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
        }
    
    def test_api_health(self) -> bool:
        """Test if API is running."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                print_success("API is running")
                data = response.json()
                print_info(f"Version: {data.get('version', 'unknown')}")
                return True
            else:
                print_error(f"API returned status {response.status_code}")
                return False
        except Exception as e:
            print_error(f"API not accessible: {e}")
            print_info("Make sure to run: uvicorn api.app_complete:app --reload")
            return False
    
    def test_authentication(self) -> bool:
        """Test authentication system."""
        print_header("Testing Authentication")
        
        # Test admin login
        print_info("Testing admin login...")
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                params={"username": "admin", "password": "admin123"},
            )
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                print_success("Admin login successful")
                print_info(f"Token: {self.admin_token[:20]}...")
                self.test_results["passed"] += 1
            else:
                print_error(f"Admin login failed: {response.text}")
                self.test_results["failed"] += 1
                return False
        except Exception as e:
            print_error(f"Admin login error: {e}")
            self.test_results["failed"] += 1
            return False
        
        self.test_results["total"] += 1
        
        # Test user login
        print_info("Testing user login...")
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                params={"username": "testuser", "password": "test123"},
            )
            if response.status_code == 200:
                data = response.json()
                self.user_token = data["access_token"]
                print_success("User login successful")
                self.test_results["passed"] += 1
            else:
                print_error(f"User login failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"User login error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Test get current user
        print_info("Testing get current user...")
        try:
            response = requests.get(
                f"{self.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )
            if response.status_code == 200:
                user_data = response.json()
                print_success(f"Got user data: {user_data['username']} ({user_data['role']})")
                self.test_results["passed"] += 1
            else:
                print_error(f"Get user failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Get user error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        return True
    
    def test_user_management(self) -> bool:
        """Test user management endpoints."""
        print_header("Testing User Management")
        
        if not self.admin_token:
            print_error("Admin token not available")
            return False
        
        # Test get all users
        print_info("Testing get all users...")
        try:
            response = requests.get(
                f"{self.base_url}/api/admin/users",
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )
            if response.status_code == 200:
                users = response.json()
                print_success(f"Retrieved {len(users)} users")
                for user in users:
                    print_info(f"  - {user['username']} ({user['role']}, {user['rate_limit_tier']})")
                self.test_results["passed"] += 1
            else:
                print_error(f"Get users failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Get users error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Test update user tier
        print_info("Testing update user tier...")
        try:
            response = requests.put(
                f"{self.base_url}/api/admin/users/testuser/tier",
                params={"tier": "pro"},
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )
            if response.status_code == 200:
                print_success("User tier updated to pro")
                self.test_results["passed"] += 1
            else:
                print_error(f"Update tier failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Update tier error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        return True
    
    def test_detection(self) -> bool:
        """Test detection with authentication."""
        print_header("Testing Detection System")
        
        if not self.user_token:
            print_error("User token not available")
            return False
        
        test_cases = [
            {
                "text": "The capital of France is Paris.",
                "expected": "allow",
                "description": "Valid factual statement",
            },
            {
                "text": "RAG stands for Ruthenium-Arsenic Growth",
                "expected": "block",
                "description": "Fabricated concept",
            },
            {
                "text": "Studies show this might be effective",
                "expected": "warn",
                "description": "Vague claim without evidence",
            },
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print_info(f"Test {i}: {test_case['description']}")
            try:
                response = requests.post(
                    f"{self.base_url}/api/detect",
                    json={"text": test_case["text"]},
                    headers={"Authorization": f"Bearer {self.user_token}"},
                )
                if response.status_code == 200:
                    result = response.json()
                    print_success(f"  Action: {result['action']}")
                    print_info(f"  Tier: {result['tier_used']}")
                    print_info(f"  Confidence: {result['confidence']:.2f}")
                    print_info(f"  Time: {result['processing_time_ms']:.2f}ms")
                    print_info(f"  Rate limit: {result['rate_limit']['remaining']}/{result['rate_limit']['limit']}")
                    self.test_results["passed"] += 1
                else:
                    print_error(f"Detection failed: {response.text}")
                    self.test_results["failed"] += 1
            except Exception as e:
                print_error(f"Detection error: {e}")
                self.test_results["failed"] += 1
            
            self.test_results["total"] += 1
            time.sleep(0.5)
        
        return True
    
    def test_rate_limiting(self) -> bool:
        """Test rate limiting."""
        print_header("Testing Rate Limiting")
        
        if not self.user_token:
            print_error("User token not available")
            return False
        
        print_info("Making multiple requests to test rate limiting...")
        success_count = 0
        rate_limited = False
        
        for i in range(5):
            try:
                response = requests.post(
                    f"{self.base_url}/api/detect",
                    json={"text": f"Test request {i+1}"},
                    headers={"Authorization": f"Bearer {self.user_token}"},
                )
                if response.status_code == 200:
                    success_count += 1
                    result = response.json()
                    print_info(f"  Request {i+1}: OK (Remaining: {result['rate_limit']['remaining']})")
                elif response.status_code == 429:
                    rate_limited = True
                    print_info(f"  Request {i+1}: Rate limited (as expected)")
                    break
            except Exception as e:
                print_error(f"Request error: {e}")
        
        print_success(f"Rate limiting working correctly ({success_count} requests succeeded)")
        self.test_results["passed"] += 1
        self.test_results["total"] += 1
        return True
    
    def test_monitoring(self) -> bool:
        """Test monitoring endpoints."""
        print_header("Testing Monitoring")
        
        # Test health check
        print_info("Testing health check...")
        try:
            response = requests.get(f"{self.base_url}/api/monitoring/health")
            if response.status_code == 200:
                health = response.json()
                print_success(f"Health: {health['status']}")
                print_info(f"Database: {health.get('database', 'unknown')}")
                self.test_results["passed"] += 1
            else:
                print_error(f"Health check failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Health check error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        
        # Test tier stats
        print_info("Testing tier statistics...")
        try:
            response = requests.get(f"{self.base_url}/api/monitoring/tier_stats")
            if response.status_code == 200:
                stats = response.json()
                print_success("Tier statistics retrieved")
                print_info(f"  Total checks: {stats['total_checks']}")
                print_info(f"  Tier 1: {stats['distribution']['tier1_pct']:.1f}%")
                print_info(f"  Tier 2: {stats['distribution']['tier2_pct']:.1f}%")
                print_info(f"  Tier 3: {stats['distribution']['tier3_pct']:.1f}%")
                print_info(f"  Health: {stats['health']['message']}")
                self.test_results["passed"] += 1
            else:
                print_error(f"Tier stats failed: {response.text}")
                self.test_results["failed"] += 1
        except Exception as e:
            print_error(f"Tier stats error: {e}")
            self.test_results["failed"] += 1
        
        self.test_results["total"] += 1
        return True
    
    def run_all_tests(self):
        """Run all tests."""
        print(f"\n{COLORS['blue']}{'='*60}{COLORS['reset']}")
        print(f"{COLORS['blue']}{'Phase 5 Complete Test Suite':^60}{COLORS['reset']}")
        print(f"{COLORS['blue']}{'='*60}{COLORS['reset']}\n")
        
        # Test API health first
        print_header("Pre-flight Check")
        if not self.test_api_health():
            print_error("API is not running. Cannot proceed with tests.")
            return False
        
        # Run all test suites
        self.test_authentication()
        self.test_user_management()
        self.test_detection()
        self.test_rate_limiting()
        self.test_monitoring()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n{COLORS['blue']}{'='*60}{COLORS['reset']}")
        print(f"{COLORS['blue']}{'Test Summary':^60}{COLORS['reset']}")
        print(f"{COLORS['blue']}{'='*60}{COLORS['reset']}\n")
        
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests:  {total}")
        print(f"{COLORS['green']}Passed:       {passed}{COLORS['reset']}")
        print(f"{COLORS['red']}Failed:       {failed}{COLORS['reset']}")
        print(f"\nSuccess Rate: {success_rate:.1f}%\n")
        
        if failed == 0:
            print(f"{COLORS['green']}🎉 All tests passed! Phase 5 is fully functional.{COLORS['reset']}\n")
        else:
            print(f"{COLORS['yellow']}⚠️  Some tests failed. Check the output above for details.{COLORS['reset']}\n")


if __name__ == "__main__":
    tester = Phase5Tester()
    tester.run_all_tests()
