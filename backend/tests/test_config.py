import os
from unittest.mock import patch

from app.config import Settings


def test_settings_loads_from_env():
    env = {
        "AZURE_SPEECH_KEY": "test-key",
        "AZURE_SPEECH_REGION": "eastus",
        "AZURE_OPENAI_KEY": "oai-key",
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    }
    with patch.dict(os.environ, env, clear=False):
        s = Settings()
    assert s.azure_speech_key == "test-key"
    assert s.azure_speech_region == "eastus"
    assert s.azure_speech_endpoint == (
        "wss://eastus.stt.speech.microsoft.com/speech/universal/v2"
    )


def test_settings_defaults_to_empty():
    s = Settings(
        azure_speech_key="",
        azure_speech_region="",
        azure_openai_key="",
        azure_openai_endpoint="",
        azure_openai_deployment="",
    )
    assert s.azure_speech_key == ""
