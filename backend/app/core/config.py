from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5433 
    postgres_user: str = "weatherflow" 
    postgres_password: str = "weatherflow" 
    postgres_db: str = "weatherflow"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()