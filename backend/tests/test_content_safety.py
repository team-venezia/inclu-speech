import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.content_safety import ContentSafetyService


def _make_service() -> ContentSafetyService:
    svc = ContentSafetyService.__new__(ContentSafetyService)
    svc._url = "https://test.cognitiveservices.azure.com/contentsafety/text:analyze?api-version=2023-10-01"
    svc._headers = {"Ocp-Apim-Subscription-Key": "test-key", "Content-Type": "application/json"}
    svc._client = MagicMock()
    return svc


def _mock_response(severities: dict[str, int]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "categoriesAnalysis": [
            {"category": cat, "severity": sev}
            for cat, sev in severities.items()
        ]
    }
    return resp


@pytest.mark.asyncio
async def test_is_safe_returns_true_for_clean_text():
    svc = _make_service()
    svc._client.post = AsyncMock(return_value=_mock_response(
        {"Hate": 0, "Violence": 0, "Sexual": 0, "SelfHarm": 0}
    ))
    assert await svc.is_safe("Hello, nice to meet you.") is True


@pytest.mark.asyncio
async def test_is_safe_returns_false_when_severity_at_threshold():
    svc = _make_service()
    svc._client.post = AsyncMock(return_value=_mock_response(
        {"Hate": 4, "Violence": 0, "Sexual": 0, "SelfHarm": 0}
    ))
    assert await svc.is_safe("flagged text") is False


@pytest.mark.asyncio
async def test_is_safe_returns_true_for_severity_below_threshold():
    svc = _make_service()
    svc._client.post = AsyncMock(return_value=_mock_response(
        {"Hate": 2, "Violence": 0, "Sexual": 0, "SelfHarm": 0}
    ))
    assert await svc.is_safe("borderline text") is True


@pytest.mark.asyncio
async def test_is_safe_fails_open_on_api_error():
    svc = _make_service()
    svc._client.post = AsyncMock(side_effect=Exception("network error"))
    assert await svc.is_safe("some text") is True


@pytest.mark.asyncio
async def test_is_safe_returns_true_for_empty_text():
    svc = _make_service()
    svc._client.post = AsyncMock()
    assert await svc.is_safe("") is True
    svc._client.post.assert_not_called()


# --- Integration test (skipped unless env vars are set) ---

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("AZURE_CONTENT_SAFETY_ENDPOINT"),
    reason="AZURE_CONTENT_SAFETY_ENDPOINT not set",
)
async def test_integration_safe_text():
    svc = ContentSafetyService(
        endpoint=os.environ["AZURE_CONTENT_SAFETY_ENDPOINT"],
        key=os.environ["AZURE_CONTENT_SAFETY_KEY"],
    )
    assert await svc.is_safe("The meeting starts at 10am.") is True
    await svc.close()
