import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # OCR
    OCR_DEFAULT_LANGUAGE: str = os.getenv("OCR_DEFAULT_LANGUAGE", "mixed")

    # Allowed file types
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "pdf"}
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # API Keys Authentication
    API_KEYS_ENABLED: bool = os.getenv("API_KEYS_ENABLED", "false").lower() == "true"
    API_KEYS: set = set(filter(None, os.getenv("API_KEYS", "").split(",")))

    # Admin Master Key (for initial setup)
    ADMIN_MASTER_KEY: str = os.getenv("ADMIN_MASTER_KEY", "")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))


settings = Settings()
