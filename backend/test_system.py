"""
Verath System Test Script
Tests all major endpoints and functionality
"""
import asyncio
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_test(test_name):
    """Print test header"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)

def print_result(success, message):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")

def test_status():
    """Test system status endpoint"""
    print_test("System Status")
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            data = response.json()
            # FIX 1: replaced non-existent 'nodes' field with actual response fields
            print_result(True, f"System is {data.get('status')}, version {data.get('version')}, scheduler {data.get('scheduler')}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_signup():
    """Test user signup"""
    print_test("User Signup")
    try:
        username = f"testuser_{datetime.now().timestamp()}"
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"username": username, "password": "testpass123"}
        )
        # FIX 2: /auth/signup returns 201 Created, not 200
        if response.status_code in (200, 201):
            data = response.json()
            print_result(True, f"User created: {username}")
            return username
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Error: {e}")
        return None

def test_login(username):
    """Test user login"""
    print_test("User Login")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": "testpass123"}
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print_result(True, f"Login successful for {username}")
            return token
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return None
    except Exception as e:
        print_result(False, f"Error: {e}")
        return None

def test_query(token):
    """Test query endpoint"""
    print_test("Query Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/query?q=what%20did%20I%20do",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            # FIX 3: guard against None answer crashing with TypeError on [:50]
            answer = data.get('answer') or ""
            print_result(True, f"Query returned: {answer[:50]}...")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_statistics(token):
    """Test statistics endpoint"""
    print_test("Statistics Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/statistics",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Statistics: {data.get('total')} memories, {data.get('recent_count')} recent")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_timeline(token):
    """Test timeline endpoint"""
    print_test("Timeline Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/timeline",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Timeline has {len(data.get('timeline', []))} items")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_insights(token):
    """Test insights endpoint"""
    print_test("Insights Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/insights",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Insights has {len(data.get('insights', []))} items")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_summary(token):
    """Test summary endpoint"""
    print_test("Summary Endpoint")
    try:
        response = requests.get(
            f"{BASE_URL}/summary",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            # same None-guard as test_query for consistency
            summary = data.get('summary') or ""
            print_result(True, f"Summary generated: {summary[:50]}...")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_speaker_train_unauthenticated():
    """Test that /speaker/train rejects unauthenticated requests"""
    print_test("Speaker Train - Unauthenticated (Regression)")
    try:
        response = requests.post(
            f"{BASE_URL}/speaker/train",
            json={"name": "Alice", "sample_text": "hello"}
        )
        if response.status_code == 401:
            print_result(True, "Unauthenticated request correctly rejected with 401")
            return True
        else:
            print_result(False, f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_speaker_profiles_unauthenticated():
    """Test that /speaker/profiles rejects unauthenticated requests"""
    print_test("Speaker Profiles - Unauthenticated (Regression)")
    try:
        response = requests.get(f"{BASE_URL}/speaker/profiles")
        if response.status_code == 401:
            print_result(True, "Unauthenticated request correctly rejected with 401")
            return True
        else:
            print_result(False, f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_speaker_train_authenticated(token):
    """Test that /speaker/train works for authenticated users"""
    print_test("Speaker Train - Authenticated")
    try:
        response = requests.post(
            f"{BASE_URL}/speaker/train",
            json={"name": "Alice", "sample_text": "hello"},
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Voice profile saved: {data.get('name')}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_speaker_profiles_authenticated(token):
    """Test that /speaker/profiles works for authenticated users"""
    print_test("Speaker Profiles - Authenticated")
    try:
        response = requests.get(
            f"{BASE_URL}/speaker/profiles",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Profiles retrieved: {data.get('profiles')}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}, Error: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Verath System Test Suite")
    print("="*60)

    # Test 1: Status
    status_ok = test_status()

    if not status_ok:
        print("\n❌ Backend is not running. Please start the backend first:")
        print("   cd backend")
        print("   python run.py")
        return

    # Test 2: Signup
    username = test_signup()

    if not username:
        print("\n❌ Signup failed. Cannot continue with authenticated tests.")
        return

    # Test 3: Login
    token = test_login(username)

    if not token:
        print("\n❌ Login failed. Cannot continue with authenticated tests.")
        return

    # FIX 4: track all results instead of unconditionally printing success
    results = []

    # Test 4: Query
    results.append(test_query(token))

    # Test 5: Statistics
    results.append(test_statistics(token))

    # Test 6: Timeline
    results.append(test_timeline(token))

    # Test 7: Insights
    results.append(test_insights(token))

    # Test 8: Summary
    results.append(test_summary(token))

    # Test 9: Speaker auth regression
    results.append(test_speaker_train_unauthenticated())
    results.append(test_speaker_profiles_unauthenticated())

    # Test 10: Speaker authenticated
    results.append(test_speaker_train_authenticated(token))
    results.append(test_speaker_profiles_authenticated(token))

    # Final summary
    print("\n" + "="*60)
    print("Test Suite Complete")
    print("="*60)

    failed = results.count(False)
    if failed == 0:
        print("\n✅ All basic endpoints are functional!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check output above.")

    print("\nNext steps:")
    print("1. Test mobile app connection")
    print("2. Test web dashboard connection")
    print("3. Test audio recording functionality")
    print("4. Test intelligent memory extraction")

if __name__ == "__main__":
    main()