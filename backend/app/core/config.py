from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "QueueFlow"
    environment: str = "development"

    database_url: str
    redis_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:5173"]

    scheduler_poll_interval_seconds: int = 10

    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "QueueFlow"

    retry_backoff_minutes: list[int] = [1, 5, 15]

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"


settings = Settings()
