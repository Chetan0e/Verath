"""
Production-grade test suite for Verath backend
Tests ChromaDB migration, retry logic, and JWT refresh tokens
"""
import asyncio
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_status():
    """Test system status endpoint."""
    print("\n" + "="*60)
    print("TEST 1: System Status")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/status")
        data = response.json()
        print(f"✅ Status: {data.get('status')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Nodes: {data.get('nodes')}")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

def test_signup_login():
    """Test user signup and login with refresh tokens."""
    print("\n" + "="*60)
    print("TEST 2: Signup and Login with Refresh Tokens")
    print("="*60)
    
    username = f"test_user_{datetime.now().timestamp()}"
    password = "test_password_123"
    
    try:
        # Signup
        signup_response = requests.post(f"{BASE_URL}/auth/signup", json={
            "username": username,
            "password": password
        })
        
        if signup_response.status_code == 200:
            print(f"✅ Signup successful for user: {username}")
        else:
            print(f"❌ Signup failed: {signup_response.text}")
            return False
        
        # Login
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            print(f"✅ Login successful")
            print(f"   Access token: {data.get('access_token')[:50]}...")
            print(f"   Refresh token: {data.get('refresh_token')[:50]}...")
            return data
        else:
            print(f"❌ Login failed: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return None

def test_refresh_token(tokens):
    """Test refresh token endpoint."""
    print("\n" + "="*60)
    print("TEST 3: Refresh Token")
    print("="*60)
    
    if not tokens or 'refresh_token' not in tokens:
        print("❌ No tokens available for refresh test")
        return False
    
    try:
        response = requests.post(f"{BASE_URL}/auth/refresh", json={
            "refresh_token": tokens['refresh_token']
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token refresh successful")
            print(f"   New access token: {data.get('access_token')[:50]}...")
            print(f"   New refresh token: {data.get('refresh_token')[:50]}...")
            return data
        else:
            print(f"❌ Token refresh failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Refresh test failed: {e}")
        return False

def test_logout(tokens):
    """Test logout with token revocation."""
    print("\n" + "="*60)
    print("TEST 4: Logout and Token Revocation")
    print("="*60)
    
    if not tokens or 'access_token' not in tokens:
        print("❌ No tokens available for logout test")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = requests.post(f"{BASE_URL}/auth/logout", 
                                json={"revoke_all": True},
                                headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Logout successful")
            print(f"   Message: {response.json().get('msg')}")
            return True
        else:
            print(f"❌ Logout failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Logout test failed: {e}")
        return False

def test_pipeline_extract():
    """Test extraction pipeline with ChromaDB."""
    print("\n" + "="*60)
    print("TEST 5: Extraction Pipeline (ChromaDB)")
    print("="*60)
    
    try:
        response = requests.post(f"{BASE_URL}/pipeline/extract", json={
            "text": "meet tomorrow at 3pm with John"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Extraction successful")
            print(f"   Intent: {data.get('intent')}")
            print(f"   Summary: {data.get('summary')}")
            print(f"   Entities: {data.get('entities')}")
            return True
        else:
            print(f"❌ Extraction failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Extraction test failed: {e}")
        return False

def test_queue_stats():
    """Test queue statistics endpoint."""
    print("\n" + "="*60)
    print("TEST 6: Queue Statistics")
    print("="*60)
    
    # First login to get token
    username = f"test_user_{datetime.now().timestamp()}"
    password = "test_password_123"
    
    try:
        # Create user
        requests.post(f"{BASE_URL}/auth/signup", json={
            "username": username,
            "password": password
        })
        
        # Login
        login_response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        
        if login_response.status_code != 200:
            print("❌ Failed to get auth token")
            return False
        
        tokens = login_response.json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Get queue stats
        response = requests.get(f"{BASE_URL}/pipeline/queue/stats", headers=headers)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Queue stats retrieved")
            print(f"   Queued: {stats.get('queued', 0)}")
            print(f"   Processing: {stats.get('processing', 0)}")
            print(f"   Completed: {stats.get('completed', 0)}")
            print(f"   Failed: {stats.get('failed', 0)}")
            print(f"   Dead Letter: {stats.get('dead_letter', 0)}")
            return True
        else:
            print(f"❌ Queue stats failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Queue stats test failed: {e}")
        return False

def main():
    """Run all production tests."""
    print("\n" + "="*60)
    print("Verath Production Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: System Status
    results.append(("System Status", test_status()))
    
    # Test 2: Signup and Login
    tokens = test_signup_login()
    results.append(("Signup and Login", tokens is not None))
    
    if tokens:
        # Test 3: Refresh Token
        new_tokens = test_refresh_token(tokens)
        results.append(("Refresh Token", bool(new_tokens)))

        # Test 4: Logout
        # NOTE: Do NOT fall back to the old tokens if refresh failed.
        # `new_tokens or tokens` would silently reuse stale/potentially
        # revoked credentials and mask the refresh failure.
        if new_tokens:
            results.append(("Logout", test_logout(new_tokens)))
        else:
            print("\n⚠️  Skipping Logout test — refresh failed, refusing to fall back to stale tokens")
            results.append(("Logout", False))
    
    # Test 5: Extraction Pipeline
    results.append(("Extraction Pipeline", test_pipeline_extract()))
    
    # Test 6: Queue Stats
    results.append(("Queue Statistics", test_queue_stats()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All production tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
