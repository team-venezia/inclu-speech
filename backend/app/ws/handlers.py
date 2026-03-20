from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

from app.config import settings
from app.services.speech import SpeechService
from app.services.translation import TranslationService

logger = logging.getLogger(__name__)


class SessionHandler:
    """Orchestrates a single transcription session."""

    def __init__(self, send_json: Callable[[dict], Awaitable[None]]):
        self._send_json = send_json
        self._speech_service: SpeechService | None = None
        self._translation_service: TranslationService | None = None
        self._translation_enabled: dict[int, str] = {}  # speaker -> target_lang
        self._loop = asyncio.get_running_loop()

    async def handle_text(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON received: %s", raw)
            return

        msg_type = msg.get("type")
        if msg_type == "start_session":
            self._start_speech_service()
            await self._send_json({"type": "session_started"})
        elif msg_type == "stop_session":
            self._stop_speech_service()
            await self._send_json({"type": "session_stopped"})
        elif msg_type == "toggle_translation":
            self._handle_toggle(msg)

    async def handle_binary(self, data: bytes) -> None:
        if self._speech_service:
            self._speech_service.push_audio(data)

    def cleanup(self) -> None:
        self._stop_speech_service()

    def _start_speech_service(self) -> None:
        self._translation_enabled = {}
        self._speech_service = SpeechService(
            speech_key=settings.azure_speech_key,
            speech_region=settings.azure_speech_region,
            on_transcript=self._on_transcript,
            on_error=self._on_error,
            loop=self._loop,
        )
        if settings.azure_openai_key:
            self._translation_service = TranslationService(
                api_key=settings.azure_openai_key,
                endpoint=settings.azure_openai_endpoint,
                deployment=settings.azure_openai_deployment,
            )
        self._speech_service.start()

    def _stop_speech_service(self) -> None:
        if self._speech_service:
            self._speech_service.stop()

    def _handle_toggle(self, msg: dict) -> None:
        speaker = msg["speaker"]
        enabled = msg["enabled"]
        target_lang = msg["targetLang"]
        if enabled:
            self._translation_enabled[speaker] = target_lang
        else:
            self._translation_enabled.pop(speaker, None)

    async def _on_transcript(
        self,
        utt_id: str,
        speaker: int,
        text: str,
        lang: str,
        is_final: bool,
        timestamp: float | None,
    ) -> None:
        msg: dict[str, Any] = {
            "type": "transcript",
            "id": utt_id,
            "speaker": speaker,
            "source": "speech",
            "text": text,
            "lang": lang,
            "isFinal": is_final,
        }
        if timestamp is not None:
            msg["timestamp"] = round(timestamp, 2)
        await self._send_json(msg)

        if is_final and speaker in self._translation_enabled and self._translation_service:
            target_lang = self._translation_enabled[speaker]
            translated = await self._translation_service.translate(text, target_lang)
            if translated:
                await self._send_json(
                    {
                        "type": "translation",
                        "refId": utt_id,
                        "speaker": speaker,
                        "text": translated,
                        "targetLang": target_lang,
                    }
                )

    async def _on_error(self, message: str, code: str) -> None:
        await self._send_json({"type": "error", "message": message, "code": code})
