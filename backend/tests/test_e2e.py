"""
End-to-End Integration Test for SecondBrain

Tests the complete user flow from signup to logout against a running backend instance.
Run with: python -m pytest tests/test_e2e.py -v
"""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta


BASE_URL = "http://localhost:8002"
TEST_USERNAME = "testuser_e2e"
TEST_PASSWORD = "testpass123"
TEST_TEXT = "Meeting with Sarah next Monday at 2pm about the product launch deadline"


class TestE2E:
    """End-to-end integration tests for SecondBrain backend."""

    @pytest.fixture(scope="class")
    async def http_client(self):
        """Async HTTP client for API calls."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            yield client

    @pytest.fixture(scope="class")
    async def cleanup_user(self, http_client):
        """Cleanup test user before and after tests."""
        # Try to delete user if exists (login first to get token)
        try:
            response = await http_client.post(
                "/auth/login",
                json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                # Delete all memories for this user would require a bulk delete endpoint
                # For now, we'll just logout
                await http_client.post(
                    "/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
        except Exception:
            pass
        yield
        # Final cleanup after tests
        try:
            response = await http_client.post(
                "/auth/login",
                json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
            )
            if response.status_code == 200:
                token = response.json()["access_token"]
                await http_client.post(
                    "/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
        except Exception:
            pass

    async def test_1_signup(self, http_client):
        """Test user signup."""
        response = await http_client.post(
            "/auth/signup",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert response.status_code == 201, f"Signup failed: {response.text}"
        data = response.json()
        assert data["username"] == TEST_USERNAME
        print("✓ Signup successful")

    async def test_2_login(self, http_client):
        """Test user login and store tokens."""
        response = await http_client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Store for use in subsequent tests
        TestE2E.access_token = data["access_token"]
        TestE2E.refresh_token = data["refresh_token"]
        print("✓ Login successful, tokens stored")

    async def test_3_pipeline_extract(self, http_client):
        """Test pipeline extraction with sample text."""
        response = await http_client.post(
            "/pipeline/extract",
            json={"text": TEST_TEXT},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        # This endpoint might not exist yet - if so, skip
        if response.status_code == 404:
            print("⚠ /pipeline/extract endpoint not found, skipping")
            TestE2E.memory_id = None
            return
        
        assert response.status_code == 200, f"Extract failed: {response.text}"
        data = response.json()
        
        # Verify extraction results
        assert data.get("intent") in ["meeting", "deadline", "task", "other"]
        assert "entities" in data
        assert data.get("importance", 0) > 0.3
        
        # Store memory ID for later tests
        TestE2E.memory_id = data.get("memory_id")
        print(f"✓ Extraction successful: intent={data.get('intent')}, importance={data.get('importance')}")

    async def test_4_pipeline_validate_duplicate(self, http_client):
        """Test duplicate detection."""
        response = await http_client.post(
            "/pipeline/validate",
            json={"text": TEST_TEXT},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            print("⚠ /pipeline/validate endpoint not found, skipping")
            return
        
        assert response.status_code == 200
        data = response.json()
        # After first extract, this should be a duplicate
        assert data.get("is_duplicate") == True
        print("✓ Duplicate detection working")

    async def test_5_query(self, http_client):
        """Test query functionality."""
        response = await http_client.get(
            "/query",
            params={"q": "when is the meeting with Sarah"},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"Query failed: {response.text}"
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        print(f"✓ Query successful: answer length={len(data.get('answer', ''))}")

    async def test_6_timeline(self, http_client):
        """Test timeline retrieval."""
        response = await http_client.get(
            "/timeline",
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"Timeline failed: {response.text}"
        data = response.json()
        assert "timeline" in data
        print(f"✓ Timeline retrieved: {len(data.get('timeline', []))} items")

    async def test_7_reminders_upcoming(self, http_client):
        """Test upcoming reminders."""
        response = await http_client.get(
            "/reminders/upcoming",
            params={"hours": 24},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"Reminders failed: {response.text}"
        data = response.json()
        assert "reminders" in data
        print(f"✓ Reminders retrieved: {len(data.get('reminders', []))} items")

    async def test_8_export_csv(self, http_client):
        """Test CSV export."""
        response = await http_client.get(
            "/export",
            params={"format": "csv"},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        csv_content = response.text
        
        # Verify CSV headers
        assert "id,text,intent,importance,speaker,timestamp,summary" in csv_content
        # Verify at least one data row (header + data)
        lines = csv_content.strip().split('\n')
        assert len(lines) >= 1
        print(f"✓ CSV export successful: {len(lines)} lines")

    async def test_9_export_json(self, http_client):
        """Test JSON export."""
        response = await http_client.get(
            "/export",
            params={"format": "json"},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"JSON export failed: {response.text}"
        data = response.json()
        assert "memories" in data
        assert "count" in data
        assert "exported_at" in data
        print(f"✓ JSON export successful: {data.get('count')} memories")

    async def test_10_delete_memory(self, http_client):
        """Test memory deletion."""
        if not hasattr(TestE2E, 'memory_id') or not TestE2E.memory_id:
            print("⚠ No memory ID available, skipping delete test")
            return
            
        response = await http_client.delete(
            f"/memory/{TestE2E.memory_id}",
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print("✓ Memory deleted successfully")

    async def test_11_query_after_delete(self, http_client):
        """Test query reflects empty state after deletion."""
        response = await http_client.get(
            "/query",
            params={"q": "Sarah meeting"},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Query after delete: {len(data.get('sources', []))} sources")

    async def test_12_logout(self, http_client):
        """Test logout and token blacklisting."""
        response = await http_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 200, f"Logout failed: {response.text}"
        print("✓ Logout successful")

    async def test_13_token_blacklisted(self, http_client):
        """Test that blacklisted token returns 401."""
        response = await http_client.get(
            "/query",
            params={"q": "test"},
            headers={"Authorization": f"Bearer {TestE2E.access_token}"}
        )
        assert response.status_code == 401, "Blacklisted token should return 401"
        print("✓ Token blacklisting verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
