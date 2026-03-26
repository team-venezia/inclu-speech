from __future__ import annotations

import logging
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)


class VisionService:
    """Azure Custom Vision prediction client."""

    def __init__(
        self,
        endpoint: str,
        prediction_key: str,
        project_id: str,
        iteration_name: str,
        confidence_threshold: float = 0.7,
    ):
        self._endpoint = endpoint.rstrip("/")
        self._prediction_key = prediction_key
        self._project_id = project_id
        self._iteration_name = iteration_name
        self._confidence_threshold = confidence_threshold
        self._client = httpx.AsyncClient(timeout=5.0)

    async def predict(self, image_data: bytes) -> Tuple[str, float] | None:
        """Classify an image and return (tag, confidence) or None."""
        url = (
            f"{self._endpoint}/customvision/v3.0/Prediction"
            f"/{self._project_id}/classify/iterations"
            f"/{self._iteration_name}/image/nostore"
        )
        headers = {
            "Prediction-Key": self._prediction_key,
            "Content-Type": "application/octet-stream",
        }
        try:
            response = await self._client.post(
                url, headers=headers, content=image_data
            )
            response.raise_for_status()
        except Exception:
            logger.exception("Custom Vision API call failed")
            return None

        predictions = response.json().get("predictions", [])
        if not predictions:
            return None

        top = max(predictions, key=lambda p: p["probability"])
        if top["probability"] < self._confidence_threshold:
            return None

        if top["tagName"].lower() == "negative":
            return None

        return top["tagName"], top["probability"]

    async def close(self) -> None:
        await self._client.aclose()
