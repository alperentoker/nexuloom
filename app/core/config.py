import logging
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet

logger = logging.getLogger("nexuloom.config")

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Nexuloom Data Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    APP_BRAND: str = "Nexuloom"
    
    # Environment & Settings (Supports both NEXULOOM_ and UDI_ prefixes)
    NEXULOOM_ENV: str = "development"
    NEXULOOM_DEBUG: bool = True
    UDI_ENV: str = "development"
    UDI_DEBUG: bool = True

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    NEXULOOM_DATA_DIR: Path = BASE_DIR / "data"
    NEXULOOM_REPORTS_DIR: Path = BASE_DIR / "reports"
    NEXULOOM_LOGS_DIR: Path = BASE_DIR / "logs"

    # Backward compatibility aliases
    @property
    def UDI_DATA_DIR(self) -> Path:
        return self.NEXULOOM_DATA_DIR

    @property
    def UDI_REPORTS_DIR(self) -> Path:
        return self.NEXULOOM_REPORTS_DIR

    @property
    def UDI_LOGS_DIR(self) -> Path:
        return self.NEXULOOM_LOGS_DIR

    # Security
    NEXULOOM_SECRET_KEY: str = "nexuloom-super-secret-key-production-ready-2026"
    UDI_SECRET_KEY: str = "nexuloom-super-secret-key-production-ready-2026"
    UDI_FERNET_KEY: str = ""

    # Query Execution & Limits
    UDI_QUERY_TIMEOUT_SECONDS: int = 30
    UDI_MAX_ROWS_RETURNED: int = 50000
    UDI_DEFAULT_PAGE_SIZE: int = 100
    UDI_CACHE_TTL_SECONDS: int = 3600

    # Internal system SQLite path
    @property
    def SYSTEM_DB_PATH(self) -> Path:
        return self.NEXULOOM_DATA_DIR / "system.db"

    @property
    def SYSTEM_DB_URL(self) -> str:
        return f"sqlite:///{self.SYSTEM_DB_PATH}"

    def ensure_directories(self) -> None:
        self.NEXULOOM_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.NEXULOOM_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (self.NEXULOOM_REPORTS_DIR / "exports").mkdir(parents=True, exist_ok=True)
        (self.NEXULOOM_REPORTS_DIR / "scheduled").mkdir(parents=True, exist_ok=True)
        self.NEXULOOM_LOGS_DIR.mkdir(parents=True, exist_ok=True)

        if not self.UDI_FERNET_KEY:
            logger.warning(
                "UDI_FERNET_KEY is not defined in environment/.env! Generated an ephemeral Fernet key. "
                "WARNING: In production, configure a static UDI_FERNET_KEY in .env to prevent database secret decryption failures upon restart."
            )
            self.UDI_FERNET_KEY = Fernet.generate_key().decode()


settings = Settings()
settings.ensure_directories()
