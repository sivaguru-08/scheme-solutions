import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() in ("true", "1")
    HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store", "schemes.db"))
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INTENT_CONFIDENCE_THRESHOLD: float = float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.45"))
    ENABLE_ACCESS_LOGS: bool = True

config = AppConfig()
