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

    await handler.handle_binary(b"\x01\x00\x01\x02\x03")

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


@pytest.mark.asyncio
async def test_handle_binary_routes_video_frame():
    """Binary frames starting with 0x02 should be treated as video frames."""
    send = AsyncMock()
    handler = SessionHandler(send_json=send)

    # Enable ASL for speaker 1 in sign_to_text direction
    handler._asl_enabled = {1: "sign_to_text"}

    jpeg_data = b"\xff\xd8fake-jpeg"
    with patch.object(handler, "_process_video_frame", new_callable=AsyncMock) as mock_proc:
        await handler.handle_binary(b"\x02" + jpeg_data)
        mock_proc.assert_called_once_with(jpeg_data)


@pytest.mark.asyncio
async def test_handle_binary_drops_unknown_prefix():
    """Binary frames with unrecognized prefix should be silently dropped."""
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    mock_speech = MagicMock()
    handler._speech_service = mock_speech

    await handler.handle_binary(b"\x03some-data")

    mock_speech.push_audio.assert_not_called()
    send.assert_not_called()


@pytest.mark.asyncio
async def test_handle_toggle_asl_enable():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)

    await handler.handle_text(
        '{"type": "toggle_asl", "speaker": 1, "enabled": true, "direction": "sign_to_text"}'
    )

    assert handler._asl_enabled[1] == "sign_to_text"


@pytest.mark.asyncio
async def test_handle_toggle_asl_disable():
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    handler._asl_enabled[1] = "sign_to_text"

    await handler.handle_text(
        '{"type": "toggle_asl", "speaker": 1, "enabled": false, "direction": "sign_to_text"}'
    )

    assert 1 not in handler._asl_enabled


@pytest.mark.asyncio
async def test_stop_session_resets_asl_state():
    """Stopping session should clear ASL toggles."""
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    handler._asl_enabled[1] = "sign_to_text"
    mock_service = MagicMock()
    mock_service.stop = MagicMock()
    handler._speech_service = mock_service

    await handler.handle_text('{"type": "stop_session"}')

    assert handler._asl_enabled == {}


@pytest.mark.asyncio
async def test_process_video_frame_deduplicates():
    """Same sign within 2s cooldown should not emit twice."""
    send = AsyncMock()
    handler = SessionHandler(send_json=send)
    handler._asl_enabled = {1: "sign_to_text"}
    handler._sign_counter = 0

    mock_vision = AsyncMock()
    mock_vision.predict = AsyncMock(return_value=("hello", 0.95))
    handler._vision_service = mock_vision

    # First call should emit
    await handler._process_video_frame(b"\xff\xd8fake")
    assert send.call_count == 1
    assert send.call_args[0][0]["text"] == "hello"

    # Second call with same sign within 2s should NOT emit
    send.reset_mock()
    await handler._process_video_frame(b"\xff\xd8fake")
    send.assert_not_called()

    # Different sign should emit
    mock_vision.predict = AsyncMock(return_value=("goodbye", 0.88))
    await handler._process_video_frame(b"\xff\xd8fake2")
    assert send.call_count == 1
    assert send.call_args[0][0]["text"] == "goodbye"
