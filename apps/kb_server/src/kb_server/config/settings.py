from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8080

    database_url: str = "postgresql://postgres:postgres@localhost:5432/kb"
    pgvector_schema: str = "public"

    auth_mode: str = "todo"
    tenant_mode: str = "todo"
