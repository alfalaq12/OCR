"""
Entry point aplikasi OCR API.
Jalanin pake: python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.routers import ocr, admin
from app.models.schemas import HealthResponse
from app.middleware.auth import RateLimitMiddleware
from app.config import settings


# deskripsi lengkap buat API docs
DESKRIPSI_API = """
# 🔍 OCR API Documentation

Selamat datang di OCR API! API ini memungkinkan Anda untuk mengekstrak teks dari dokumen scan seperti gambar dan PDF.

---

## 🚀 Fitur Utama

| Fitur | Keterangan |
|-------|------------|
| 📄 **Image OCR** | Baca teks dari PNG, JPG, TIFF, BMP, GIF |
| 📑 **PDF OCR** | Support multi-halaman dengan output per halaman |
| 🌐 **Multi Bahasa** | Indonesia dan English |
| 📦 **MinIO Integration** | Proses file langsung dari object storage |
| 🔐 **API Key Auth** | Keamanan dengan API key |
| ⏱️ **Rate Limiting** | Perlindungan dari spam request |
| 📊 **History & Stats** | Lacak penggunaan API |

---

## 🔑 Autentikasi

Untuk menggunakan API, tambahkan header:
```
X-API-Key: <your-api-key>
```

Hubungi administrator untuk mendapatkan API key.

---

## 📝 Format Response

Semua endpoint mengembalikan format JSON yang konsisten:

```json
{
  "success": true,
  "text": "Hasil ekstraksi teks...",
  "pages": 1,
  "language": "mixed",
  "processing_time_ms": 1234,
  "error": null,
  "error_code": null
}
```

---

## ⚠️ Error Codes

| Kode | Deskripsi |
|------|-----------|
| `AUTH_MISSING_KEY` | API key tidak ditemukan di header |
| `AUTH_INVALID_KEY` | API key tidak valid |
| `FILE_TYPE_NOT_ALLOWED` | Format file tidak didukung |
| `FILE_TOO_LARGE` | Ukuran file melebihi 50MB |
| `OCR_ENGINE_ERROR` | Gagal memproses OCR |
| `PDF_CONVERSION_ERROR` | Gagal mengkonversi PDF |
| `RATE_LIMIT_EXCEEDED` | Terlalu banyak request |

---

## 📞 Dukungan

Jika mengalami kendala, silakan hubungi tim teknis.
"""

# metadata untuk tags
TAGS_METADATA = [
    {
        "name": "OCR",
        "description": "**Endpoint utama** untuk ekstraksi teks dari dokumen. Upload file atau ambil dari MinIO.",
    },
    {
        "name": "Admin",
        "description": "**Manajemen API Key**. Memerlukan akses admin (X-Admin-Key header).",
    },
]


app = FastAPI(
    title="🔍 OCR API",
    description=DESKRIPSI_API,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Tim Development",
        "email": "support@example.com",
    },
    license_info={
        "name": "Proprietary",
    },
)


# custom OpenAPI schema biar lebih bagus
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="🔍 OCR API",
        version="1.0.0",
        description=DESKRIPSI_API,
        routes=app.routes,
        tags=TAGS_METADATA,
    )
    
    # tambahin logo (optional - bisa diganti URL logo sendiri)
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


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


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """
    🏠 **Health Check**
    
    Endpoint untuk mengecek apakah server berjalan normal.
    
    Returns:
    - **status**: Status server (healthy/unhealthy)
    - **version**: Versi API
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    💓 **Health Check (Alternatif)**
    
    Endpoint alternatif untuk health check, biasanya digunakan oleh load balancer.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )
