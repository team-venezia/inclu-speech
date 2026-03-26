from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Severity levels: 0 = safe, 2 = low, 4 = medium, 6 = high
_BLOCK_THRESHOLD = 4


class ContentSafetyService:
    """Azure AI Content Safety — text moderation for transcript entries."""

    def __init__(self, endpoint: str, key: str):
        self._url = (
            f"{endpoint.rstrip('/')}/contentsafety/text:analyze"
            "?api-version=2023-10-01"
        )
        self._headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=3.0)

    async def is_safe(self, text: str) -> bool:
        """Return True if text passes moderation, False if it should be suppressed."""
        if not text.strip():
            return True
        try:
            response = await self._client.post(
                self._url,
                headers=self._headers,
                json={
                    "text": text,
                    "categories": ["Hate", "Violence", "Sexual", "SelfHarm"],
                    "outputType": "FourSeverityLevels",
                },
            )
            response.raise_for_status()
        except Exception:
            logger.exception("Content Safety API call failed — allowing entry through")
            return True  # fail open: don't block speech due to API errors

        for item in response.json().get("categoriesAnalysis", []):
            if item.get("severity", 0) >= _BLOCK_THRESHOLD:
                logger.warning(
                    "Content Safety blocked entry (category=%s severity=%s): %r",
                    item.get("category"),
                    item.get("severity"),
                    text,
                )
                return False
        return True

    async def close(self) -> None:
        await self._client.aclose()
