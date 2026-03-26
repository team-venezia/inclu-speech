from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

from app.config import settings
from app.services.content_safety import ContentSafetyService
from app.services.speech import SpeechService
from app.services.summarization import SummarizationService
from app.services.translation import TranslationService
from app.services.vision import VisionService

logger = logging.getLogger(__name__)

_AUDIO_PREFIX = 0x01
_VIDEO_PREFIX = 0x02


class SessionHandler:
    """Orchestrates a single transcription session."""

    def __init__(self, send_json: Callable[[dict], Awaitable[None]]):
        self._send_json = send_json
        self._speech_service: SpeechService | None = None
        self._translation_service: TranslationService | None = None
        self._vision_service: VisionService | None = None
        self._translation_enabled: dict[int, str] = {}  # speaker -> target_lang
        self._asl_enabled: dict[int, str] = {}  # speaker -> direction
        self._sign_counter: int = 0
        self._prediction_in_flight: bool = False
        self._last_sign: dict[int, tuple[str, float]] = {}  # speaker -> (tag, timestamp)
        self._loop = asyncio.get_running_loop()
        self._transcript_log: list[dict] = []
        self._summarization_service: SummarizationService | None = None
        self._content_safety_service: ContentSafetyService | None = None

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
            if self._transcript_log and self._summarization_service:
                try:
                    result = await self._summarization_service.summarize(self._transcript_log)
                    await self._send_json({
                        "type": "summary",
                        "speakers": {str(spk): data for spk, data in result.items()},
                    })
                except Exception:
                    logger.exception("Summarization failed")
            await self._send_json({"type": "session_stopped"})
            self._transcript_log = []
        elif msg_type == "toggle_translation":
            self._handle_toggle(msg)
        elif msg_type == "toggle_asl":
            self._handle_toggle_asl(msg)

    async def handle_binary(self, data: bytes) -> None:
        if not data:
            return
        prefix = data[0]
        payload = data[1:]
        if prefix == _AUDIO_PREFIX:
            if self._speech_service:
                self._speech_service.push_audio(payload)
        elif prefix == _VIDEO_PREFIX:
            if self._asl_enabled:
                await self._process_video_frame(payload)
        else:
            logger.warning("Unknown binary frame prefix: 0x%02x", prefix)

    def cleanup(self) -> None:
        self._stop_speech_service()

    def _start_speech_service(self) -> None:
        self._translation_enabled = {}
        self._asl_enabled = {}
        self._sign_counter = 0
        self._last_sign = {}
        self._transcript_log = []
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
            self._summarization_service = SummarizationService(
                api_key=settings.azure_openai_key,
                endpoint=settings.azure_openai_endpoint,
                deployment=settings.azure_openai_deployment,
            )
        if settings.azure_content_safety_endpoint:
            self._content_safety_service = ContentSafetyService(
                endpoint=settings.azure_content_safety_endpoint,
                key=settings.azure_content_safety_key,
            )
        if settings.azure_custom_vision_endpoint:
            self._vision_service = VisionService(
                endpoint=settings.azure_custom_vision_endpoint,
                prediction_key=settings.azure_custom_vision_prediction_key,
                project_id=settings.azure_custom_vision_project_id,
                iteration_name=settings.azure_custom_vision_iteration_name,
                confidence_threshold=0.85,
            )
        self._speech_service.start()

    def _stop_speech_service(self) -> None:
        if self._speech_service:
            self._speech_service.stop()
            self._speech_service = None
        self._asl_enabled = {}
        self._vision_service = None

    def _handle_toggle(self, msg: dict) -> None:
        try:
            speaker = msg["speaker"]
            enabled = msg["enabled"]
            target_lang = msg["targetLang"]
        except KeyError:
            logger.warning("Malformed toggle_translation message: %s", msg)
            return
        if enabled:
            self._translation_enabled[speaker] = target_lang
        else:
            self._translation_enabled.pop(speaker, None)

    def _handle_toggle_asl(self, msg: dict) -> None:
        try:
            speaker = msg["speaker"]
            enabled = msg["enabled"]
            direction = msg["direction"]
        except KeyError:
            logger.warning("Malformed toggle_asl message: %s", msg)
            return
        if enabled:
            self._asl_enabled[speaker] = direction
        else:
            self._asl_enabled.pop(speaker, None)

    async def _process_video_frame(self, image_data: bytes) -> None:
        if self._prediction_in_flight or not self._vision_service:
            return
        self._prediction_in_flight = True
        try:
            result = await self._vision_service.predict(image_data)
            if result is None:
                return
            tag, confidence = result
            # Find which speaker has sign_to_text enabled
            speaker = next(
                (s for s, d in self._asl_enabled.items() if d == "sign_to_text"),
                None,
            )
            if speaker is None:
                return
            # Deduplication: skip if same sign within 2s cooldown
            now = self._loop.time()
            last = self._last_sign.get(speaker)
            if last and last[0] == tag and (now - last[1]) < 2.0:
                return
            self._last_sign[speaker] = (tag, now)
            self._transcript_log.append({"speaker": speaker, "text": tag, "source": "sign"})
            self._sign_counter += 1
            sign_id = f"sign-{self._sign_counter:04d}"
            await self._send_json({
                "type": "transcript",
                "id": sign_id,
                "speaker": speaker,
                "source": "sign",
                "text": tag,
                "lang": "asl",
                "isFinal": True,
                "confidence": round(confidence, 2),
            })

            if speaker in self._translation_enabled and self._translation_service:
                try:
                    translated = await self._translation_service.translate(tag, "es")
                    if translated:
                        await self._send_json({
                            "type": "translation",
                            "refId": sign_id,
                            "speaker": speaker,
                            "text": translated,
                            "targetLang": "es",
                        })
                except Exception:
                    logger.exception("Translation failed for sign %s", sign_id)
        except Exception:
            logger.exception("Video frame processing failed")
        finally:
            self._prediction_in_flight = False

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

        if is_final and self._content_safety_service:
            if not await self._content_safety_service.is_safe(text):
                return
        await self._send_json(msg)

        if is_final:
            self._transcript_log.append({"speaker": speaker, "text": text, "source": "speech"})

        if is_final and speaker in self._translation_enabled and self._translation_service:
            # Dynamically infer target: translate to the "other" language
            target_lang = "en" if lang.startswith("es") else "es"
            try:
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
            except Exception:
                logger.exception("Translation failed for utterance %s", utt_id)

    async def _on_error(self, message: str, code: str) -> None:
        await self._send_json({"type": "error", "message": message, "code": code})
