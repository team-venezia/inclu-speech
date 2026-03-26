from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.summarization import SummarizationService


SAMPLE_ENTRIES = [
    {"speaker": 1, "text": "Hello everyone, let's start the meeting.", "source": "speech"},
    {"speaker": 2, "text": "Thanks for joining. I'll present the roadmap.", "source": "speech"},
    {"speaker": 1, "text": "Great, please go ahead.", "source": "speech"},
    {"speaker": 2, "text": "Q1 goals include shipping the new feature.", "source": "sign"},
]

VALID_SUMMARY_JSON = json.dumps({
    "1": {
        "en": ["Started the meeting.", "Welcomed speaker 2 to present."],
        "es": ["Inició la reunión.", "Le dio la bienvenida al orador 2."],
    },
    "2": {
        "en": ["Presented the Q1 roadmap.", "Mentioned shipping a new feature."],
        "es": ["Presentó la hoja de ruta del Q1.", "Mencionó el lanzamiento de una nueva función."],
    },
})


@pytest.mark.asyncio
async def test_summarize_happy_path():
    """Mock a valid API response and assert int keys and correct structure."""
    svc = SummarizationService.__new__(SummarizationService)
    svc._client = MagicMock()
    svc._deployment = "gpt-4o"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=VALID_SUMMARY_JSON))]

    with pytest.MonkeyPatch().context() as mp:
        svc._client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await svc.summarize(SAMPLE_ENTRIES)

    assert isinstance(result, dict)
    # Keys must be ints
    assert all(isinstance(k, int) for k in result)
    assert 1 in result
    assert 2 in result
    # Each speaker entry has "en" and "es" lists
    for speaker_id, langs in result.items():
        assert "en" in langs
        assert "es" in langs
        assert isinstance(langs["en"], list)
        assert isinstance(langs["es"], list)
        assert len(langs["en"]) > 0
        assert len(langs["es"]) > 0


def _make_service() -> SummarizationService:
    svc = SummarizationService.__new__(SummarizationService)
    svc._client = MagicMock()
    svc._deployment = "gpt-4o"
    return svc


@pytest.mark.asyncio
async def test_summarize_empty_entries_returns_empty():
    svc = _make_service()
    result = await svc.summarize([])
    assert result == {}


@pytest.mark.asyncio
async def test_summarize_api_error_raises():
    """When the API call fails, summarize() should propagate the exception."""
    svc = SummarizationService.__new__(SummarizationService)
    svc._client = MagicMock()
    svc._deployment = "gpt-4o"

    svc._client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))

    with pytest.raises(Exception, match="API down"):
        await svc.summarize(SAMPLE_ENTRIES)


@pytest.mark.asyncio
async def test_summarize_malformed_json_raises():
    """When the model returns non-JSON content, summarize() should raise JSONDecodeError."""
    svc = SummarizationService.__new__(SummarizationService)
    svc._client = MagicMock()
    svc._deployment = "gpt-4o"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="not json at all"))]
    svc._client.chat.completions.create = AsyncMock(return_value=mock_response)

    with pytest.raises(json.JSONDecodeError):
        await svc.summarize(SAMPLE_ENTRIES)
