import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.vision import VisionService


@pytest.mark.asyncio
async def test_predict_returns_top_tag_above_threshold():
    service = VisionService(
        endpoint="https://test.cognitiveservices.azure.com",
        prediction_key="test-key",
        project_id="test-project",
        iteration_name="Iteration1",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "predictions": [
            {"tagName": "hello", "probability": 0.95},
            {"tagName": "goodbye", "probability": 0.03},
        ]
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        tag, confidence = await service.predict(b"\xff\xd8fake-jpeg")

    assert tag == "hello"
    assert confidence == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_predict_returns_none_below_threshold():
    service = VisionService(
        endpoint="https://test.cognitiveservices.azure.com",
        prediction_key="test-key",
        project_id="test-project",
        iteration_name="Iteration1",
        confidence_threshold=0.7,
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "predictions": [
            {"tagName": "hello", "probability": 0.5},
        ]
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.predict(b"\xff\xd8fake-jpeg")

    assert result is None


@pytest.mark.asyncio
async def test_predict_returns_none_on_api_error():
    service = VisionService(
        endpoint="https://test.cognitiveservices.azure.com",
        prediction_key="test-key",
        project_id="test-project",
        iteration_name="Iteration1",
    )
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = Exception("500 error")

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.predict(b"\xff\xd8fake-jpeg")

    assert result is None


@pytest.mark.asyncio
async def test_predict_returns_none_on_empty_predictions():
    service = VisionService(
        endpoint="https://test.cognitiveservices.azure.com",
        prediction_key="test-key",
        project_id="test-project",
        iteration_name="Iteration1",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"predictions": []}

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.predict(b"\xff\xd8fake-jpeg")

    assert result is None
