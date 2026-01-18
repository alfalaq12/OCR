"""
Entry point untuk Document OCR Service.
Server dijalankan dengan: python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import ocr, admin, learning
from app.models.schemas import HealthResponse
from app.middleware.auth import RateLimitMiddleware
from app.config import settings
import os


# Dokumentasi API untuk enterprise clients
API_DESCRIPTION = """
Layanan ekstraksi teks otomatis dari dokumen scan. 

📖 **Dokumentasi lengkap:** [/api-docs](/api-docs)
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
        "name": "Learning Dictionary",
        "description": "Export/import learned words dan manajemen dictionary learning. Memerlukan akses administrator.",
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
    redoc_url=None,  # Disabled, use /api-docs instead
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "bintang",
        "email": "bintangal.falag@gmail.com",
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
app.include_router(learning.router)

# Mount static files untuk UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/ui", tags=["Health"])
async def serve_ui():
    """Serve documentation UI untuk client."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "UI not found"}


@app.get("/api-docs", tags=["Health"])
async def serve_api_docs():
    """Serve modern API documentation page."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "api-docs.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "API docs not found"}


@app.on_event("startup")
async def startup_event():
    """Initialize OCR engines saat startup."""
    from app.services.ocr_service import ocr_service
    print("Initializing OCR engines...")
    ocr_service.init_engine()
    engines = ocr_service.get_available_engines()
    print(f"OCR ready! Available: {engines}, Default: {ocr_service.get_engine_name()}")
    
    # Load learned words dari database ke dictionary
    try:
        from app.services.dictionary_corrector import load_learned_words
        count = load_learned_words()
        print(f"Dictionary ready! Loaded {count} learned words from database")
    except Exception as e:
        print(f"Could not load learned words: {e}")


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
