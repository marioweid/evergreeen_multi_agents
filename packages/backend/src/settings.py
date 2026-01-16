from typing import Literal
from pydantic import Field, AliasChoices, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


    database_url: PostgresDsn
    google_api_key: str = Field( validation_alias=AliasChoices('GOOGLE_API_KEY', 'GEMINI_API_KEY'))
    embedding_model: Literal["models/text-embedding-004", "gemini-embedding-001"] = "models/text-embedding-004"
    embedding_dimensions: Literal[768, 1536, 3072] = 768