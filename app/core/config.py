# 用途：读取 MG_ 环境变量和本项目 .env，校验配置并隐藏数据库地址与密钥的显示值。
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MG_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "MeterGate"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    jwt_secret: SecretStr | None = None
    jwt_issuer: str = Field(default="metergate", min_length=1)
    jwt_audience: str = Field(default="metergate-api", min_length=1)
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    health_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
