"""
Router untuk admin - manage API keys.
Butuh X-Admin-Key header buat akses.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from app.models.schemas import (
    APIKeyCreateRequest, APIKeyResponse, APIKeyInfo, 
    APIKeyListResponse, APIKeyStatsResponse
)
from app.services.db_service import db_service
from app.config import settings
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def cek_akses_admin(x_admin_key: Optional[str] = Header(None, description="Admin key untuk akses")):
    """
    Verifikasi akses admin.
    Bisa pake master key dari .env atau API key yang is_admin=true.
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Admin key diperlukan",
                "error_code": "ADMIN_KEY_REQUIRED",
                "details": "Tambahin header X-Admin-Key"
            }
        )
    
    # cek master key dari env
    if settings.ADMIN_MASTER_KEY and x_admin_key == settings.ADMIN_MASTER_KEY:
        return "master"
    
    # cek apakah admin API key dari database
    if db_service.cek_admin_key(x_admin_key):
        return x_admin_key
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Admin key tidak valid",
            "error_code": "ADMIN_KEY_INVALID",
            "details": "Key yang dikasih salah atau bukan admin"
        }
    )


@router.post("/keys", response_model=APIKeyResponse)
async def buat_api_key(
    request: APIKeyCreateRequest,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    🔑 **Generate API Key Baru**
    
    Buat API key baru untuk client. Key hanya ditampilkan **SEKALI**, 
    pastikan langsung disimpan!
    
    **Parameter:**
    - **name**: Nama/deskripsi key (misal: "Client Pak Faris")
    - **is_admin**: Set `true` untuk buat admin key
    
    **Contoh Request:**
    ```json
    {
      "name": "Client Pak Faris",
      "is_admin": false
    }
    ```
    
    **⚠️ PENTING:** Simpan key yang dikembalikan, tidak bisa dilihat lagi!
    """
    hasil = db_service.bikin_api_key(
        nama=request.name,
        is_admin=request.is_admin
    )
    
    return APIKeyResponse(**hasil)


@router.get("/keys", response_model=APIKeyListResponse)
async def list_api_keys(admin_key: str = Depends(cek_akses_admin)):
    """
    📋 **Daftar Semua API Keys**
    
    Lihat semua API key yang terdaftar beserta statistik penggunaan.
    
    **Note:** Key asli tidak ditampilkan, hanya prefix-nya saja.
    """
    keys = db_service.list_api_keys()
    
    return APIKeyListResponse(
        total=len(keys),
        keys=[
            APIKeyInfo(
                id=k["id"],
                key_prefix=k["key_prefix"],
                name=k["name"],
                is_admin=bool(k["is_admin"]),
                is_active=bool(k["is_active"]),
                requests_count=k["requests_count"] or 0,
                last_used_at=k["last_used_at"],
                created_at=k["created_at"],
                revoked_at=k["revoked_at"]
            )
            for k in keys
        ]
    )


@router.delete("/keys/{key_id}")
async def cabut_api_key(
    key_id: int,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    🚫 **Nonaktifkan API Key**
    
    Cabut/revoke API key sehingga tidak bisa digunakan lagi.
    
    **Parameter:**
    - **key_id**: ID dari API key yang ingin dinonaktifkan
    """
    berhasil = db_service.cabut_api_key(key_id)
    
    if not berhasil:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "API key tidak ditemukan",
                "error_code": "KEY_NOT_FOUND"
            }
        )
    
    return {"success": True, "message": f"API key {key_id} sudah dinonaktifkan"}


@router.get("/keys/stats", response_model=APIKeyStatsResponse)
async def stats_api_key(admin_key: str = Depends(cek_akses_admin)):
    """
    📈 **Statistik API Keys**
    
    Lihat ringkasan statistik semua API key.
    
    **Response:**
    - Total keys
    - Keys aktif
    - Keys yang sudah di-revoke
    - Total request dari semua key
    """
    stats = db_service.stats_api_key()
    return APIKeyStatsResponse(**stats)
