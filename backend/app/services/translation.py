from __future__ import annotations

import logging

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

_META_RESPONSE_MARKERS = (
    "entrenado con datos",
    "trained with data",
    "knowledge cutoff",
    "fecha de corte",
    "cut-off date",
    "training data",
    "datos de entrenamiento",
    "october 2023",
    "octubre de 2023",
)


class TranslationService:
    def __init__(self, api_key: str, endpoint: str, deployment: str):
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
        )
        self._deployment = deployment

    async def translate(self, text: str, target_lang: str) -> str | None:
        if not text.strip():
            return None

        lang_names = {"en": "English", "es": "Spanish"}
        target = lang_names.get(target_lang, target_lang)

        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a translator. Translate the user's text to {target}. "
                        "Output only the translated text with no explanations, comments, or additional content."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        result = response.choices[0].message.content
        if result and any(marker in result.lower() for marker in _META_RESPONSE_MARKERS):
            logger.warning("Translation returned a model meta-response, discarding: %r", result)
            return None
        return result
