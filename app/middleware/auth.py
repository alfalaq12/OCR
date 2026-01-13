"""
Middleware untuk autentikasi dan rate limiting.
"""

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from app.config import settings

# header untuk API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Cek API key dari header request"""
    
    # kalo auth dimatikan, langsung lolos
    if not settings.API_KEYS_ENABLED:
        return "anonymous"
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "API key diperlukan",
                "error_code": "AUTH_MISSING_KEY",
                "details": "Tambahin header X-API-Key"
            }
        )
    
    # cek key statis dari .env
    if api_key in settings.API_KEYS:
        return api_key
    
    # cek key dinamis dari database
    from app.services.db_service import db_service
    info_key = db_service.validasi_api_key(api_key)
    if info_key:
        return api_key
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "API key tidak valid",
            "error_code": "AUTH_INVALID_KEY",
            "details": "Key yang dikasih salah atau sudah kadaluarsa"
        }
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware buat batasi jumlah request per menit.
    Biar server gak overload kalo ada yang spam.
    """
    
    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.batas_per_menit = requests_per_minute
        self.catatan_request = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # skip rate limit buat halaman dokumentasi
        path_dikecualikan = ["/", "/health", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in path_dikecualikan:
            return await call_next(request)
        
        # identifikasi client dari API key atau IP
        api_key = request.headers.get("X-API-Key")
        id_client = api_key if api_key else request.client.host
        
        # hitung request dalam 1 menit terakhir
        sekarang = time.time()
        semenit_lalu = sekarang - 60
        
        # bersihin catatan yang udah lewat 1 menit
        self.catatan_request[id_client] = [
            waktu for waktu in self.catatan_request[id_client]
            if waktu > semenit_lalu
        ]
        
        # cek udah kena limit belum
        if len(self.catatan_request[id_client]) >= self.batas_per_menit:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Kebanyakan request, coba lagi nanti",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "details": f"Maksimal {self.batas_per_menit} request per menit"
                }
            )
        
        # catat request ini
        self.catatan_request[id_client].append(sekarang)
        
        # tambahin info rate limit di response header
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.batas_per_menit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.batas_per_menit - len(self.catatan_request[id_client])
        )
        
        return response
