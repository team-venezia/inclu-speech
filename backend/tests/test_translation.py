from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.translation import TranslationService


@pytest.mark.asyncio
async def test_translate_returns_translated_text():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hello, I need help."))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    service = TranslationService.__new__(TranslationService)
    service._client = mock_client
    service._deployment = "gpt-4o"

    result = await service.translate("Hola, necesito ayuda.", "en")
    assert result == "Hello, I need help."


@pytest.mark.asyncio
async def test_translate_returns_none_on_empty_input():
    service = TranslationService.__new__(TranslationService)
    service._client = MagicMock()
    service._deployment = "gpt-4o"

    result = await service.translate("", "en")
    assert result is None
