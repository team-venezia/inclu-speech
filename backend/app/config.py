from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_openai_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""

    @property
    def azure_speech_endpoint(self) -> str:
        return (
            f"wss://{self.azure_speech_region}"
            f".stt.speech.microsoft.com/speech/universal/v2"
        )

    model_config = {"env_file": ".env"}


settings = Settings()
