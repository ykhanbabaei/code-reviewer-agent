import logging
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings



class MonitoringConfig(BaseSettings):
    """Observability and monitoring configuration"""

    # LangSmith (for LangGraph tracing)

    # Logging
    log_level: int = Field(default=logging.INFO)
    log_format: str = Field(default="json")  # json or console
    log_file: str = Field(default="./app.log")

class DatabaseConfig(BaseSettings):
    # Qdrant config
    qdrant_db_path: Optional[str] = Field(default=os.getenv('QDRANT_STORAGE_PATH'))

class LLMConfig(BaseSettings):
    hugging_face_api_key: Optional[str] = Field(default=os.getenv('HF_TOKEN'))
    hugging_face_embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")

class RankerConfig(BaseSettings):
    top_n: int = Field(default=3)

class Settings(BaseSettings):
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ranker: RankerConfig = Field(default_factory=RankerConfig)
    IS_MOCK: bool = Field(default=False)


settings = Settings()
