from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _candidate_env_files() -> tuple[str, ...]:
    """Busca el `.env` en varias ubicaciones razonables.

    Permite ejecutar uvicorn desde `mockup/backend` y seguir leyendo el
    archivo `mockup/.env` (donde vive la configuración real del entorno).
    """
    here = Path(__file__).resolve()
    candidates: list[str] = [".env"]
    for parents_up in range(2, 6):
        try:
            base = here.parents[parents_up]
        except IndexError:
            continue
        candidates.append(str(base / ".env"))
    return tuple(candidates)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_candidate_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")

    postgres_user: str = Field(default="upvearth", alias="POSTGRES_USER")
    postgres_password: str = Field(default="upvearth", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="upvearth", alias="POSTGRES_DB")
    postgres_host: str = Field(default="db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    max_upload_size_mb: int = Field(default=30, alias="MAX_UPLOAD_SIZE_MB")
    upload_dir: str = Field(default="/app/data/uploads", alias="UPLOAD_DIR")

    embeddings_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDINGS_MODEL_NAME",
    )
    pb_reference_csv: str = Field(
        default="/app/corpus_PB/data/pb_reference.csv",
        alias="PB_REFERENCE_CSV",
    )
    pb_top_k: int = Field(default=3, alias="PB_TOP_K")

    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    ollama_url: str = Field(default="http://127.0.0.1:11434/api/generate", alias="OLLAMA_URL")
    ollama_model_name: str = Field(default="qwen2.5:14b", alias="OLLAMA_MODEL_NAME")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")

    # OpenAI-compatible LLM (vLLM o llama-cpp-python) para el chatbot RAG.
    # Independiente de Ollama (que sigue usándose para el scoring PB del pipeline).
    llm_base_url: str = Field(default="http://localhost:8001/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="qwen3-8b-instruct", alias="LLM_MODEL")
    llm_api_key: str = Field(default="local-key", alias="LLM_API_KEY")
    llm_request_timeout: int = Field(default=120, alias="LLM_REQUEST_TIMEOUT")
    llm_max_tokens: int = Field(default=512, alias="LLM_MAX_TOKENS")
    chat_temperature: float = Field(default=0.2, alias="CHAT_TEMPERATURE")

    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
