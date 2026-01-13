"""
Entry point aplikasi OCR API.
Jalanin pake: python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ocr, admin
from app.models.schemas import HealthResponse
from app.middleware.auth import RateLimitMiddleware
from app.config import settings

app = FastAPI(
    title="OCR API",
    description="""
API untuk ekstrak text dari dokumen scan.

## Fitur Utama
- Baca text dari gambar (PNG, JPG, TIFF, dll)
- Baca text dari PDF (support banyak halaman)
- Support bahasa Indonesia dan Inggris
- Integrasi dengan MinIO storage
- Autentikasi pakai API key
- Rate limiting biar server aman
- History dan statistik penggunaan

## Cara Pakai
1. Upload file ke endpoint /api/ocr/extract
2. Atau pakai file dari MinIO lewat /api/ocr/extract-from-minio
3. Hasil OCR dikembalikan dalam format JSON

## Error Codes
- AUTH_xxx = masalah autentikasi
- FILE_xxx = masalah file yang diupload
- OCR_xxx = masalah waktu proses OCR
- MINIO_xxx = masalah koneksi MinIO
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# izinin akses dari domain manapun (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# aktifin rate limiting kalo di-enable
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )

# daftarin semua router
app.include_router(ocr.router)
app.include_router(admin.router)


@app.get("/", response_model=HealthResponse)
async def root():
    """Cek apakah server jalan"""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint alternatif buat health check"""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )
