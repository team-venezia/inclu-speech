from __future__ import annotations

from openai import AsyncAzureOpenAI


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
                        f"Translate the following text to {target}. "
                        "Return only the translation, nothing else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        return response.choices[0].message.content
