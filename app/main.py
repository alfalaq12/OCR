"""
Entry point untuk Document OCR Service.
Server dijalankan dengan: python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.routers import ocr, admin
from app.models.schemas import HealthResponse
from app.middleware.auth import RateLimitMiddleware
from app.config import settings


# Dokumentasi API untuk enterprise clients
API_DESCRIPTION = """
# Document OCR Service

Layanan ekstraksi teks otomatis dari dokumen scan untuk kebutuhan digitalisasi arsip dan otomasi data entry.

---

## Kemampuan Utama

| Fitur | Spesifikasi |
|-------|-------------|
| **Format Input** | PNG, JPG, JPEG, TIFF, BMP, GIF, PDF |
| **PDF Multi-halaman** | Mendukung hingga 100+ halaman per dokumen |
| **Bahasa** | Indonesia, English, Mixed |
| **Akurasi** | 95%+ untuk dokumen berkualitas baik |
| **Response Time** | ~3-6 detik per halaman |

---

## Autentikasi

Setiap request memerlukan API Key yang valid pada header:

```
X-API-Key: <api-key-anda>
```

Untuk mendapatkan API Key, hubungi administrator sistem.

---

## Contoh Response

```json
{
  "success": true,
  "text": "Hasil ekstraksi teks dari dokumen...",
  "pages": 5,
  "language": "id",
  "processing_time_ms": 15234,
  "error": null,
  "error_code": null
}
```

---

## Kode Error

| Kode | Deskripsi |
|------|-----------|
| `AUTH_MISSING_KEY` | Header X-API-Key tidak ditemukan |
| `AUTH_INVALID_KEY` | API Key tidak valid atau sudah expired |
| `FILE_TYPE_NOT_ALLOWED` | Format file tidak didukung |
| `FILE_TOO_LARGE` | Ukuran file melebihi batas 50MB |
| `OCR_ENGINE_ERROR` | Terjadi kesalahan pada proses OCR |
| `PDF_CONVERSION_ERROR` | Gagal mengkonversi halaman PDF |
| `RATE_LIMIT_EXCEEDED` | Batas request per menit terlampaui |

---

## Kontak Teknis

Untuk pertanyaan teknis atau integrasi, silakan hubungi tim development.
"""

# Metadata untuk grouping endpoint
TAGS_METADATA = [
    {
        "name": "OCR",
        "description": "Endpoint untuk ekstraksi teks dari file dokumen. Mendukung upload langsung atau integrasi MinIO.",
    },
    {
        "name": "Admin",
        "description": "Manajemen API Key dan monitoring penggunaan. Memerlukan akses administrator.",
    },
    {
        "name": "Health",
        "description": "Status dan health check untuk monitoring infrastructure.",
    },
]


app = FastAPI(
    title="Document OCR Service",
    description=API_DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Tim Development",
        "email": "dev@company.id",
    },
    license_info={
        "name": "Proprietary License",
    },
)


def custom_openapi():
    """Generate custom OpenAPI schema dengan branding yang konsisten."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Document OCR Service",
        version="1.0.0",
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=TAGS_METADATA,
    )
    
    # Logo untuk ReDoc (opsional - ganti dengan URL logo perusahaan)
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# CORS configuration untuk akses dari berbagai domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting untuk mencegah abuse
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )

# Register routers
app.include_router(ocr.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    """Initialize OCR engine saat startup biar nggak race condition pas parallel processing."""
    from app.services.ocr_service import ocr_service
    print("🚀 Initializing OCR engine...")
    ocr_service.init_engine()
    print(f"✅ OCR ready! Engine: {ocr_service.get_engine_name()}")


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """
    Root endpoint yang mengembalikan status server.
    
    Digunakan untuk verifikasi bahwa service berjalan dengan normal.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint untuk monitoring dan load balancer.
    
    Mengembalikan status server dan versi API yang sedang berjalan.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )
