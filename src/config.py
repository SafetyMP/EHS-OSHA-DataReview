"""
Configuration management using environment variables and defaults.
"""

import os
from pathlib import Path
from typing import Optional

# Try to import pydantic_settings, fallback to pydantic
try:
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    try:
        from pydantic import BaseSettings
        PYDANTIC_AVAILABLE = True
    except ImportError:
        # Minimal fallback - just use a basic class
        PYDANTIC_AVAILABLE = False
        class BaseSettings:
            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"
                case_sensitive = False


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    database_url: Optional[str] = None
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Cache settings
    cache_ttl: int = 3600  # 1 hour
    cache_max_size: int = 1000
    redis_url: Optional[str] = None  # Optional Redis for distributed caching
    
    # API settings
    api_rate_limit: int = 100  # Requests per minute
    api_max_query_rows: int = 10000
    
    # Data settings
    data_dir: Optional[str] = None  # type: ignore
    
    # Fuzzy matching
    fuzzy_threshold: int = 75
    
    # Performance
    enable_caching: bool = True
    enable_connection_pooling: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow arbitrary types for pydantic compatibility
        arbitrary_types_allowed = True
    
    def get_data_dir(self) -> Path:
        """Get data directory path."""
        data_dir_value = getattr(self, 'data_dir', None)
        if data_dir_value:
            return Path(data_dir_value)
        return Path(__file__).parent.parent / "data"
    
    def get_database_url(self, data_dir: Optional[Path] = None) -> str:
        """Get database URL."""
        db_url = getattr(self, 'database_url', None)
        if db_url:
            return db_url
        
        data_dir = data_dir or self.get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{data_dir / 'compliance.db'}"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)."""
    global _settings
    if _settings is None:
        if PYDANTIC_AVAILABLE:
            try:
                _settings = Settings()
            except Exception as e:
                # Fallback if pydantic initialization fails
                import warnings
                warnings.warn(f"Failed to load settings: {e}. Using defaults.")
                _settings = _create_fallback_settings()
        else:
            _settings = _create_fallback_settings()
    return _settings


def _create_fallback_settings() -> Settings:
    """Create a fallback settings object with defaults."""
    settings = Settings.__new__(Settings)
    # Set default values
    settings.database_url = None
    settings.database_pool_size = 10
    settings.database_max_overflow = 20
    settings.cache_ttl = 3600
    settings.cache_max_size = 1000
    settings.redis_url = None
    settings.api_rate_limit = 100
    settings.api_max_query_rows = 10000
    settings.data_dir = None
    settings.fuzzy_threshold = 75
    settings.enable_caching = True
    settings.enable_connection_pooling = True
    settings.log_level = "INFO"
    return settings


def reload_settings():
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings

