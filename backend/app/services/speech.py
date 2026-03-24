from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.languageconfig import (
    AutoDetectSourceLanguageConfig,
)


class SpeechService:
    """Wraps Azure ConversationTranscriber with speaker mapping and event dispatch."""

    def __init__(
        self,
        speech_key: str,
        speech_region: str,
        on_transcript: Callable[..., Awaitable[None]] | None = None,
        on_error: Callable[..., Awaitable[None]] | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._speech_key = speech_key
        self._speech_region = speech_region
        self._on_transcript = on_transcript
        self._on_error = on_error
        self._loop = loop or asyncio.get_running_loop()
        self._audio_stream: speechsdk.audio.PushAudioInputStream | None = None
        self._transcriber: speechsdk.transcription.ConversationTranscriber | None = None
        self._speaker_map: dict[str, int] = {}
        self._last_active_speaker: int = 1
        self._utterance_counter: int = 0
        self._partial_ids: dict[int, str] = {}  # speaker -> current partial utterance id

    def start(self) -> None:
        endpoint = (
            f"wss://{self._speech_region}"
            f".stt.speech.microsoft.com/speech/universal/v2"
        )
        speech_config = speechsdk.SpeechConfig(
            endpoint=endpoint, subscription=self._speech_key
        )
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults,
            "true",
        )
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode,
            "Continuous",
        )

        auto_detect_config = AutoDetectSourceLanguageConfig(
            languages=["en-US", "es-ES"]
        )

        self._audio_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=self._audio_stream)

        self._transcriber = speechsdk.transcription.ConversationTranscriber(
            speech_config=speech_config,
            audio_config=audio_config,
            auto_detect_source_language_config=auto_detect_config,
        )

        self._transcriber.transcribing.connect(self._handle_transcribing)
        self._transcriber.transcribed.connect(self._handle_transcribed)
        self._transcriber.canceled.connect(self._handle_canceled)

        self._speaker_map = {}
        self._last_active_speaker = 1
        self._utterance_counter = 0
        self._partial_ids = {}

        self._transcriber.start_transcribing_async().get()

    def push_audio(self, data: bytes) -> None:
        if self._audio_stream:
            self._audio_stream.write(data)

    def stop(self) -> None:
        if self._transcriber:
            self._transcriber.stop_transcribing_async().get()
            self._transcriber = None
        if self._audio_stream:
            self._audio_stream.close()
            self._audio_stream = None

    def _map_speaker(self, speaker_id: str) -> int:
        if not speaker_id or speaker_id == "Unknown":
            return self._last_active_speaker
        if speaker_id not in self._speaker_map:
            if len(self._speaker_map) < 2:
                self._speaker_map[speaker_id] = len(self._speaker_map) + 1
            else:
                return self._last_active_speaker
        mapped = self._speaker_map[speaker_id]
        self._last_active_speaker = mapped
        return mapped

    def _get_partial_id(self, speaker: int) -> str:
        if speaker not in self._partial_ids:
            self._utterance_counter += 1
            self._partial_ids[speaker] = f"utt-{self._utterance_counter:04d}"
        return self._partial_ids[speaker]

    def _finalize_partial_id(self, speaker: int) -> str:
        utt_id = self._get_partial_id(speaker)
        self._partial_ids.pop(speaker, None)
        return utt_id

    def _detect_language(self, evt: Any) -> str:
        try:
            result = evt.result
            lang_key = speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
            return result.properties.get(lang_key, "")
        except Exception:
            return ""

    def _dispatch(self, coro: Awaitable[None]) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _handle_transcribing(self, evt: Any) -> None:
        if not self._on_transcript or not evt.result.text:
            return
        speaker = self._map_speaker(evt.result.speaker_id)
        utt_id = self._get_partial_id(speaker)
        lang = self._detect_language(evt)
        self._dispatch(
            self._on_transcript(utt_id, speaker, evt.result.text, lang, False, None)
        )

    def _handle_transcribed(self, evt: Any) -> None:
        if not self._on_transcript or not evt.result.text:
            return
        speaker = self._map_speaker(evt.result.speaker_id)
        utt_id = self._finalize_partial_id(speaker)
        lang = self._detect_language(evt)
        offset_seconds = evt.result.offset / 10_000_000  # ticks to seconds
        self._dispatch(
            self._on_transcript(
                utt_id, speaker, evt.result.text, lang, True, offset_seconds
            )
        )

    def _handle_canceled(self, evt: Any) -> None:
        if not self._on_error:
            return
        reason = evt.cancellation_details.reason
        if reason == speechsdk.CancellationReason.Error:
            error_msg = evt.cancellation_details.error_details
            self._dispatch(
                self._on_error(error_msg, "SPEECH_DISCONNECTED")
            )
