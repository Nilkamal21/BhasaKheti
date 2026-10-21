from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "BhasaKheti"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    DATABASE_URL: str = "sqlite:///./bhasakheti.db"
    
    # Model artifact paths
    PLANT_DISEASE_MODEL_PATH: str = "../plant_disease_classifier.pth"
    PLANT_DISEASE_LABELS_PATH: str = "../models/label_mappings/plant_disease_labels.json"
    SOIL_TYPE_MODEL_PATH: str = "../soil_type_classifier.tflite"
    SOIL_TYPE_LABELS_PATH: str = "../models/label_mappings/soil_type_labels.json"
    SOIL_MOISTURE_MODEL_PATH: str = "../soil_moisture_classifier.tflite"
    SOIL_MOISTURE_LABELS_PATH: str = "../models/label_mappings/soil_moisture_labels.json"
    
    # Knowledge Base Path
    KNOWLEDGE_BASE_PATH: str = "../models/knowledge_base/agricultural_knowledge.json"

    # Phase 7: Market Intelligence & Government Schemes
    MARKET_DATA_PATH: str = "../models/market_data/west_bengal_mandi_prices.json"
    SCHEMES_DATA_PATH: str = "../models/schemes_data/agricultural_schemes.json"
    MARKET_CACHE_TTL_SECONDS: int = 1800  # 30 minutes cache TTL
    MARKET_API_URL: Optional[str] = None
    MARKET_API_KEY: Optional[str] = None

    # Image upload configuration
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # Weather Service Configuration (Open-Meteo)
    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_API_BASE_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_REQUEST_TIMEOUT_SECONDS: float = 8.0
    WEATHER_CACHE_TTL_SECONDS: int = 900  # 15 minutes cache TTL

    # LLM Provider Configuration (Cohere)
    COHERE_API_KEY: Optional[str] = None
    COHERE_MODEL: str = "command-r-08-2024"
    LLM_TIMEOUT_SECONDS: float = 25.0
    LLM_TEMPERATURE: float = 0.2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
