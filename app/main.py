from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ocr, admin
from app.models.schemas import HealthResponse
from app.middleware.auth import RateLimitMiddleware
from app.config import settings

app = FastAPI(
    title="OCR API",
    description="""
API untuk extract text dari dokumen scan (image/PDF).

## Features
- 📄 Extract text dari image (PNG, JPG, TIFF, dll)
- 📑 Extract text dari PDF (multi-page support)
- 🌐 Support bahasa Indonesia dan English
- 📦 Integrasi MinIO storage
- 🔐 API Key authentication & management
- ⏱️ Rate limiting
- 📊 Request history & statistics

## Error Codes
Semua error response include `error_code` untuk debugging:
- `AUTH_xxx` - Authentication errors
- `FILE_xxx` - File validation errors
- `OCR_xxx` - OCR processing errors
- `PDF_xxx` - PDF conversion errors
- `MINIO_xxx` - MinIO storage errors

## Admin Endpoints
Untuk manage API keys, gunakan `/api/admin/keys` endpoints dengan `X-Admin-Key` header.
    """,
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
    )

# Include routers
app.include_router(ocr.router)
app.include_router(admin.router)


@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.1.0"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Alternative health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.1.0"
    )
