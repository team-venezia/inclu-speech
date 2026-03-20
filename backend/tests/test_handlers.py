import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ws.handlers import SessionHandler


@pytest.mark.asyncio
async def test_handle_start_session():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)

    with patch.object(handler, "_start_speech_service"):
        await handler.handle_text('{"type": "start_session", "config": {"sampleRate": 16000}}')

    send.assert_called_once()
    msg = send.call_args[0][0]
    assert msg["type"] == "session_started"


@pytest.mark.asyncio
async def test_handle_stop_session():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    mock_service = MagicMock()
    mock_service.stop = MagicMock()
    handler._speech_service = mock_service

    await handler.handle_text('{"type": "stop_session"}')

    mock_service.stop.assert_called_once()
    calls = [c[0][0] for c in send.call_args_list]
    assert any(m["type"] == "session_stopped" for m in calls)


@pytest.mark.asyncio
async def test_handle_binary_pushes_audio():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    mock_speech = MagicMock()
    handler._speech_service = mock_speech

    await handler.handle_binary(b"\x00\x01\x02\x03")

    mock_speech.push_audio.assert_called_once_with(b"\x00\x01\x02\x03")


@pytest.mark.asyncio
async def test_handle_toggle_translation():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)

    await handler.handle_text(
        '{"type": "toggle_translation", "speaker": 1, "targetLang": "en", "enabled": true}'
    )

    assert handler._translation_enabled[1] == "en"


@pytest.mark.asyncio
async def test_handle_toggle_translation_disable():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    handler._translation_enabled[1] = "en"

    await handler.handle_text(
        '{"type": "toggle_translation", "speaker": 1, "targetLang": "en", "enabled": false}'
    )

    assert 1 not in handler._translation_enabled
