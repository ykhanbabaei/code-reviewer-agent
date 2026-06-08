import logging
import sys
from typing import Optional, TextIO, Union

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings



class MonitoringConfig(BaseSettings):
    """Observability and monitoring configuration"""

    # LangSmith (for LangGraph tracing)

    # Logging
    log_level: int = Field(default=logging.INFO)
    log_format: str = Field(default="json")  # json or console
    log_file: str = Field(default="./app.log")


class Settings(BaseSettings):
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    IS_MOCK: bool = Field(default=False)


settings = Settings()
