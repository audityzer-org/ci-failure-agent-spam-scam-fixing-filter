"""Configuration management for Predictive Suggestions Service."""
import os
from typing import Optional
from enum import Enum


class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Config:
    """Base configuration class."""
    
    # Application settings
    APP_NAME = "Predictive Suggestions Service"
    APP_VERSION = "1.0.0"
    ENV = Environment(os.getenv("ENVIRONMENT", "development"))
    
    # Database configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/ci_failure_db"
    )
    SQLALCHEMY_ECHO = ENV == Environment.DEVELOPMENT
    SQLALCHEMY_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    
    # Redis cache configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/4")
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours
    CACHE_KEY_PREFIX = "predictions:"
    
    # AI/ML configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    AI_MODEL_NAME = os.getenv("AI_MODEL", "gemini-2.0-flash")
    AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2048"))
    
    # API configuration
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    DEBUG = ENV == Environment.DEVELOPMENT
    WORKERS = int(os.getenv("WORKERS", "4"))
    
    # Service endpoints
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_INTERVAL", "30"))  # seconds
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Prediction confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = int(os.getenv("HIGH_CONFIDENCE_THRESHOLD", "75"))
    MEDIUM_CONFIDENCE_THRESHOLD = int(os.getenv("MEDIUM_CONFIDENCE_THRESHOLD", "50"))
    

        # Lowercase property accessors for compatibility
    @property
    def environment(self):
        """Get environment as lowercase accessor."""
        return self.ENV
    
    @property
    def database_url(self):
        """Get database URL as lowercase accessor."""
        return self.DATABASE_URL
    
    @property
    def redis_url(self):
        """Get Redis URL as lowercase accessor."""
        return self.REDIS_URL
    
    @property
    def google_api_key(self):
        """Get Google API key as lowercase accessor."""
        return self.GOOGLE_API_KEY
    
    @property
    def api_timeout(self):
        """Get API timeout as lowercase accessor."""
        return self.REQUEST_TIMEOUT
    
    @property
    def max_retries(self):
        """Get max retries as lowercase accessor."""
        return getattr(self, 'MAX_RETRIES', 3)  # Default fallback
    
    @property
    def log_level(self):
        """Get log level as lowercase accessor."""
        return self.LOG_LEVEL
    
    @classmethod
    def get_config(cls) -> "Config":
        """Get configuration based on environment."""
        return cls()


# Configuration instances
config = Config.get_config()

# Module-level get_config function for easy import
def get_config() -> Config:
    """Get the configuration instance."""
    return config
