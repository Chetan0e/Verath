import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock
from app.services.auth import create_access_token


class TestFinalReleaseGateContracts:
    """Verification of release gate API contracts and compatibility aliases."""

    @pytest.mark.asyncio
    async def test_extract_and_pipeline_extract_aliases_work_identically(self, client: AsyncClient, monkeypatch):
        """Both /extract and /pipeline/extract must extract and persist memories when authenticated."""
        user_token = create_access_token("test_gate_user")
        headers = {"Authorization": f"Bearer {user_token}"}

        mock_extraction = {
            "cleaned_text": "Meeting with team tomorrow at 2pm",
            "intent": "meeting",
            "entities": {"dates": [{"phrase": "tomorrow at 2pm", "parsed_date": "2026-10-19T14:00:00", "is_relative": True}]},
            "summary": "Team meeting scheduled",
            "has_correction": False,
            "importance_boost": 0.2,
            "importance": 0.8,
        }

        mock_store = AsyncMock(return_value="mem_gate_12345")
        monkeypatch.setattr("app.services.memory_store.store_memory", mock_store)
        monkeypatch.setattr("app.pipeline.extraction_pipeline.extraction_pipeline.extract", AsyncMock(return_value=mock_extraction))

        # Test POST /extract
        res_extract = await client.post(
            "/extract",
            json={"text": "Meeting with team tomorrow at 2pm"},
            headers=headers
        )
        assert res_extract.status_code == 200
        data_extract = res_extract.json()
        assert data_extract["intent"] == "meeting"
        assert data_extract["memory_id"] == "mem_gate_12345"
        assert data_extract["success"] is True

        # Test POST /pipeline/extract alias
        res_pipeline = await client.post(
            "/pipeline/extract",
            json={"text": "Meeting with team tomorrow at 2pm"},
            headers=headers
        )
        assert res_pipeline.status_code == 200
        data_pipeline = res_pipeline.json()
        assert data_pipeline["intent"] == "meeting"
        assert data_pipeline["memory_id"] == "mem_gate_12345"
        assert data_pipeline["success"] is True

    @pytest.mark.asyncio
    async def test_extract_rejects_invalid_inputs(self, client: AsyncClient):
        """Both empty text and oversized text must be rejected with 400."""
        user_token = create_access_token("test_gate_user")
        headers = {"Authorization": f"Bearer {user_token}"}

        # Empty
        res_empty = await client.post("/extract", json={"text": ""}, headers=headers)
        assert res_empty.status_code == 400

        # Too short (<2 chars)
        res_short = await client.post("/pipeline/extract", json={"text": "a"}, headers=headers)
        assert res_short.status_code == 400

        # Oversized (>10000 chars)
        res_long = await client.post("/extract", json={"text": "x" * 10001}, headers=headers)
        assert res_long.status_code == 400

    @pytest.mark.asyncio
    async def test_reminders_ack_and_acknowledge_aliases(self, client: AsyncClient, monkeypatch):
        """Both /reminders/{id}/acknowledge and /reminders/{id}/ack must mark reminders as acknowledged."""
        user_token = create_access_token("test_gate_user")
        headers = {"Authorization": f"Bearer {user_token}"}

        ack_calls = []

        async def mock_ack(alert_id, user_id):
            if alert_id.startswith("valid_"):
                ack_calls.append((alert_id, user_id))
                return True
            return False

        monkeypatch.setattr("app.services.reminder_service.acknowledge_reminder", mock_ack)

        # 1. /acknowledge
        res_ack1 = await client.post("/reminders/valid_alert_1/acknowledge", headers=headers)
        assert res_ack1.status_code == 200
        assert res_ack1.json()["alert_id"] == "valid_alert_1"

        # 2. /ack alias
        res_ack2 = await client.post("/reminders/valid_alert_2/ack", headers=headers)
        assert res_ack2.status_code == 200
        assert res_ack2.json()["alert_id"] == "valid_alert_2"

        # 3. Not found
        res_not_found = await client.post("/reminders/missing_alert/ack", headers=headers)
        assert res_not_found.status_code == 404

    @pytest.mark.asyncio
    async def test_speaker_routes_and_aliases(self, client: AsyncClient, monkeypatch):
        """Both /train and /speaker/train, /profiles and /speaker/profiles must work."""
        user_token = create_access_token("speaker_user")
        headers = {"Authorization": f"Bearer {user_token}"}

        saved_voices = {}

        def mock_add_voice(username, name, emb):
            saved_voices[name] = username

        def mock_get_profiles(username):
            return [name for name, u in saved_voices.items() if u == username]

        monkeypatch.setattr("app.routes.speaker.add_voice", mock_add_voice)
        monkeypatch.setattr("app.routes.speaker.get_voice_profiles", mock_get_profiles)
        monkeypatch.setattr("app.routes.speaker.get_embedding", lambda text: [0.1] * 768)

        # /train
        res_t1 = await client.post("/train", json={"name": "AliceVoice", "sample_text": "Hello"}, headers=headers)
        assert res_t1.status_code == 200

        # /speaker/train alias
        res_t2 = await client.post("/speaker/train", json={"name": "BobVoice", "sample_text": "Hey"}, headers=headers)
        assert res_t2.status_code == 200

        # /profiles
        res_p1 = await client.get("/profiles", headers=headers)
        assert res_p1.status_code == 200
        assert "AliceVoice" in res_p1.json()["profiles"]
        assert "BobVoice" in res_p1.json()["profiles"]

        # /speaker/profiles alias
        res_p2 = await client.get("/speaker/profiles", headers=headers)
        assert res_p2.status_code == 200
        assert "AliceVoice" in res_p2.json()["profiles"]

    @pytest.mark.asyncio
    async def test_privacy_routes_both_with_and_without_trailing_slash(self, client: AsyncClient, monkeypatch):
        """GET /privacy and GET /privacy/ must both return 200 without 307 redirect."""
        user_token = create_access_token("privacy_user")
        headers = {"Authorization": f"Bearer {user_token}"}

        monkeypatch.setattr("app.routes.privacy.is_private", AsyncMock(return_value=False))

        res1 = await client.get("/privacy", headers=headers)
        assert res1.status_code == 200
        assert res1.json() == {"private": False}

        res2 = await client.get("/privacy/", headers=headers)
        assert res2.status_code == 200
        assert res2.json() == {"private": False}
