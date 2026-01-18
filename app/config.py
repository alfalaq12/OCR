"""
Konfigurasi aplikasi.
Semua setting diambil dari environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # koneksi MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # setting OCR
    OCR_DEFAULT_LANGUAGE: str = os.getenv("OCR_DEFAULT_LANGUAGE", "mixed")

    # Performance tuning - bisa di override via .env
    PDF_DPI: int = int(os.getenv("PDF_DPI", "150"))  # 150 lebih cepat, 200 lebih akurat
    USE_ANGLE_CLS: bool = os.getenv("USE_ANGLE_CLS", "false").lower() == "true"  # matiin kalo dokumen udah lurus
    MAX_IMAGE_DIMENSION: int = int(os.getenv("MAX_IMAGE_DIMENSION", "2000"))  # resize gambar gede
    
    # Deteksi environment Docker - matikan parallel processing untuk stabilitas
    IS_DOCKER: bool = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER", "false").lower() == "true"
    
    # Parallel processing - auto disable di Docker untuk mencegah crash
    _parallel_default = "false" if IS_DOCKER else "true"
    PARALLEL_PDF_PROCESSING: bool = os.getenv("PARALLEL_PDF_PROCESSING", _parallel_default).lower() == "true"
    PDF_WORKERS: int = int(os.getenv("PDF_WORKERS", "2"))  # kurangi default worker
    
    # Force Tesseract saat enhance aktif - sekarang disabled karena pakai OpenCV preprocessing
    FORCE_TESSERACT_FOR_ENHANCE: bool = os.getenv("FORCE_TESSERACT_FOR_ENHANCE", "false").lower() == "true"
    
    # Default enhance - untuk dokumen jadul/pudar, aktifkan preprocessing otomatis
    DEFAULT_ENHANCE: bool = os.getenv("DEFAULT_ENHANCE", "false").lower() == "true"

    # tipe file yang diperbolehkan
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "pdf"}
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # autentikasi API key
    API_KEYS_ENABLED: bool = os.getenv("API_KEYS_ENABLED", "false").lower() == "true"
    API_KEYS: set = set(filter(None, os.getenv("API_KEYS", "").split(",")))

    # master key untuk admin (buat setup awal)
    ADMIN_MASTER_KEY: str = os.getenv("ADMIN_MASTER_KEY", "")

    # rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))


settings = Settings()
