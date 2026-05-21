from app.services.auth import create_access_token
from app.services.privacy import is_private, toggle_privacy


class TestPrivacy:
    """Test privacy controls."""

    async def test_privacy_endpoints_require_authentication(self, client):
        response = await client.get("/privacy/")
        assert response.status_code == 401

        response = await client.post("/privacy/toggle")
        assert response.status_code == 401

    async def test_privacy_toggle_is_scoped_to_each_user(self, client, auth_headers):
        other_headers = {"Authorization": f"Bearer {create_access_token('other_user')}"}

        response = await client.post("/privacy/toggle", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["private"] is True

        response = await client.get("/privacy/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["private"] is True

        response = await client.get("/privacy/", headers=other_headers)
        assert response.status_code == 200
        assert response.json()["private"] is False

    async def test_toggle_privacy_helper_flips_state(self):
        user_id = "helper_user"
        first_state = toggle_privacy(user_id)
        second_state = toggle_privacy(user_id)

        assert first_state is True
        assert second_state is False
        assert is_private(user_id) is False