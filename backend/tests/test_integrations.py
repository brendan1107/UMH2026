"""Tests for external integrations and upload filename validation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── GLM Client ────────────────────────────────────────────────────────────────

class TestGLMClient:
    """Unit tests for the GLM API client."""

    def test_initialization(self):
        from app.integrations.glm_client import GLMClient

        glm = GLMClient()
        assert hasattr(glm, "api_key")
        assert hasattr(glm, "base_url")
        assert hasattr(glm, "model")
        assert hasattr(glm, "max_tokens")

    @pytest.mark.asyncio
    async def test_chat_completion_strips_markdown_fence(self):
        """chat_completion should unwrap markdown json fences from the response."""
        from app.integrations.glm_client import GLMClient

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '```json\n{"answer": 42}\n```'}}]
        }

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            glm = GLMClient()
            result = await glm.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful.",
            )

        assert result == '{"answer": 42}'

    @pytest.mark.asyncio
    async def test_chat_completion_plain_content(self):
        """chat_completion should return plain content unchanged."""
        from app.integrations.glm_client import GLMClient

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello, world!"}}]
        }

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            glm = GLMClient()
            result = await glm.chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                system="Be concise.",
            )

        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_health_check_true_on_200(self):
        """health_check returns True when the API responds with HTTP 200."""
        from app.integrations.glm_client import GLMClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            glm = GLMClient()
            result = await glm.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_false_on_error(self):
        """health_check returns False when the request raises an exception."""
        from app.integrations.glm_client import GLMClient

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            glm = GLMClient()
            result = await glm.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_false_on_non_200(self):
        """health_check returns False for non-200 status codes."""
        from app.integrations.glm_client import GLMClient

        mock_resp = MagicMock()
        mock_resp.status_code = 503

        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_resp
            )
            glm = GLMClient()
            result = await glm.health_check()

        assert result is False


# ── Google Places Client ──────────────────────────────────────────────────────

class TestGooglePlacesClient:
    """Unit tests for the Google Places API client stubs."""

    def test_initialization(self):
        from app.integrations.google_places import GooglePlacesClient

        places = GooglePlacesClient()
        assert hasattr(places, "api_key")

    @pytest.mark.asyncio
    async def test_nearby_search_stub(self):
        """nearby_search is not yet implemented; should return None."""
        from app.integrations.google_places import GooglePlacesClient

        result = await GooglePlacesClient().nearby_search(3.1390, 101.6869)
        assert result is None

    @pytest.mark.asyncio
    async def test_text_search_stub(self):
        """text_search is not yet implemented; should return None."""
        from app.integrations.google_places import GooglePlacesClient

        result = await GooglePlacesClient().text_search("bubble tea near KLCC")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_place_details_stub(self):
        """get_place_details is not yet implemented; should return None."""
        from app.integrations.google_places import GooglePlacesClient

        result = await GooglePlacesClient().get_place_details("ChIJtest")
        assert result is None


# ── Upload filename validation ────────────────────────────────────────────────

class TestUploadFilenameValidation:
    """Unit tests for _validate_upload_filename in the uploads route."""

    def test_valid_pdf(self):
        from app.api.routes.uploads import _validate_upload_filename

        assert _validate_upload_filename("report.pdf") == ".pdf"

    def test_valid_jpg(self):
        from app.api.routes.uploads import _validate_upload_filename

        assert _validate_upload_filename("photo.jpg") == ".jpg"

    def test_valid_csv(self):
        from app.api.routes.uploads import _validate_upload_filename

        assert _validate_upload_filename("data.csv") == ".csv"

    def test_valid_xlsx(self):
        from app.api.routes.uploads import _validate_upload_filename

        assert _validate_upload_filename("financials.xlsx") == ".xlsx"

    def test_blocked_sensitive_filename(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("firebase-service-account.json")
        assert exc_info.value.status_code == 400

    def test_blocked_env_backend_filename(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("env.backend")
        assert exc_info.value.status_code == 400

    def test_blocked_pem_extension(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("private.pem")
        assert exc_info.value.status_code == 400

    def test_blocked_key_extension(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("secrets.key")
        assert exc_info.value.status_code == 400

    def test_unsupported_extension(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("malware.exe")
        assert exc_info.value.status_code == 400

    def test_empty_filename(self):
        from fastapi import HTTPException
        from app.api.routes.uploads import _validate_upload_filename

        with pytest.raises(HTTPException) as exc_info:
            _validate_upload_filename("")
        assert exc_info.value.status_code == 400
