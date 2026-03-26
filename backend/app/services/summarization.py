from __future__ import annotations

import json

from openai import AsyncAzureOpenAI


class SummarizationService:
    def __init__(self, api_key: str, endpoint: str, deployment: str):
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
        )
        self._deployment = deployment

    async def summarize(
        self,
        entries: list[dict],
    ) -> dict[int, dict[str, list[str]]]:
        """Summarize meeting transcript entries grouped by speaker.

        Args:
            entries: List of dicts with keys "speaker" (int), "text" (str),
                     and "source" (str, e.g. "speech" or "sign").

        Returns:
            Dict mapping speaker id (int) to a dict of language -> bullet list,
            e.g. {1: {"en": [...], "es": [...]}, 2: {"en": [...], "es": [...]}}.

        Raises:
            Exception: If the API call fails.
            json.JSONDecodeError: If the model returns malformed JSON.
        """
        if not entries:
            return {}

        # Group entries by speaker, tagging each line with its source label.
        grouped: dict[int, list[str]] = {}
        for entry in entries:
            speaker_id: int = entry["speaker"]
            source_label = "[speech]" if entry.get("source") == "speech" else "[sign]"
            line = f"{source_label} {entry['text']}"
            grouped.setdefault(speaker_id, []).append(line)

        # Build a human-readable block for the prompt.
        transcript_block = ""
        for speaker_id, lines in sorted(grouped.items()):
            transcript_block += f"Speaker {speaker_id}:\n"
            for line in lines:
                transcript_block += f"  {line}\n"

        system_prompt = (
            "You are a meeting summarization assistant. "
            "Given a meeting transcript grouped by speaker, produce a JSON object "
            "where each key is a speaker number (as a string) and each value is an object "
            "with keys \"en\" and \"es\", each containing a list of 3–7 concise bullet points "
            "summarizing that speaker's contributions. "
            "Return only valid JSON, no additional text."
        )

        user_prompt = (
            "Summarize the following meeting transcript. "
            "Lines are tagged [speech] (spoken) or [sign] (sign language).\n\n"
            f"{transcript_block}"
        )

        response = await self._client.chat.completions.create(
            model=self._deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("GPT-4o returned empty content")
        data: dict = json.loads(raw)
        return {int(k): v for k, v in data.items()}
