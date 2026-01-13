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
    PARALLEL_PDF_PROCESSING: bool = os.getenv("PARALLEL_PDF_PROCESSING", "true").lower() == "true"  # proses halaman paralel
    PDF_WORKERS: int = int(os.getenv("PDF_WORKERS", "4"))  # jumlah worker untuk parallel processing

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
