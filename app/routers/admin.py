"""Router untuk manajemen API Key.
Memerlukan X-Admin-Key header untuk akses semua endpoint.
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
    Verifikasi akses admin menggunakan master key atau API key dengan flag is_admin.
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Admin key diperlukan",
                "error_code": "ADMIN_KEY_REQUIRED",
                "details": "Tambahkan header X-Admin-Key"
            }
        )
    
    # Cek master key dari environment
    if settings.ADMIN_MASTER_KEY and x_admin_key == settings.ADMIN_MASTER_KEY:
        return "master"
    
    # Cek admin API key dari database
    if db_service.cek_admin_key(x_admin_key):
        return x_admin_key
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Admin key tidak valid",
            "error_code": "ADMIN_KEY_INVALID",
            "details": "Key yang diberikan tidak valid atau bukan admin"
        }
    )


@router.post("/keys", response_model=APIKeyResponse)
async def buat_api_key(
    request: APIKeyCreateRequest,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Membuat API Key baru untuk client.
    
    Key hanya ditampilkan sekali saat pembuatan, pastikan langsung disimpan
    karena tidak dapat dilihat kembali.
    """
    hasil = db_service.bikin_api_key(
        nama=request.name,
        is_admin=request.is_admin
    )
    
    return APIKeyResponse(**hasil)


@router.get("/keys", response_model=APIKeyListResponse)
async def list_api_keys(admin_key: str = Depends(cek_akses_admin)):
    """
    Mengambil daftar semua API Key yang terdaftar.
    
    Key asli tidak ditampilkan untuk keamanan, hanya prefix-nya saja.
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
    Menonaktifkan API Key sehingga tidak dapat digunakan lagi.
    
    Operasi ini bersifat permanen dan tidak dapat dibatalkan.
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
    Mengambil ringkasan statistik penggunaan API Key.
    
    Menampilkan total keys, keys aktif, keys revoked, dan total request.
    """
    stats = db_service.stats_api_key()
    return APIKeyStatsResponse(**stats)


# ==================== Dashboard Endpoints ====================

from app.models.schemas import (
    DashboardStatsResponse, RequestsChartData, 
    AuditSummaryResponse, AuditEventCount
)
from app.services.learning_service import learning_service
from app.services.audit_logger import audit_logger
from datetime import datetime, timedelta


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(admin_key: str = Depends(cek_akses_admin)):
    """
    Mengambil semua statistik untuk admin dashboard.
    
    Menggabungkan data dari OCR, API Keys, Learning, dan Audit.
    """
    # OCR Stats
    ocr_stats = db_service.ambil_stats()
    
    # API Key Stats
    key_stats = db_service.stats_api_key()
    
    # Learning Stats
    learning_stats = learning_service.get_stats()
    
    # Audit Stats
    audit_stats = audit_logger.get_stats()
    
    # Calculate success rate
    total = ocr_stats["total_requests"]
    success_rate = (ocr_stats["successful"] / total * 100) if total > 0 else 0
    
    return DashboardStatsResponse(
        # OCR
        total_requests=ocr_stats["total_requests"],
        successful_requests=ocr_stats["successful"],
        failed_requests=ocr_stats["failed"],
        success_rate=round(success_rate, 1),
        avg_processing_time_ms=ocr_stats["avg_processing_time_ms"],
        total_pages_processed=ocr_stats["total_pages_processed"],
        # API Keys
        total_keys=key_stats["total_keys"],
        active_keys=key_stats["active_keys"],
        revoked_keys=key_stats["revoked_keys"],
        # Learning
        total_tracked_words=learning_stats["total_tracked"],
        approved_words=learning_stats["approved"],
        pending_words=learning_stats["pending"],
        # Audit
        total_audit_events=audit_stats.get("total", 0)
    )


@router.get("/dashboard/requests-chart", response_model=RequestsChartData)
async def get_requests_chart(
    days: int = 7,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Mengambil data untuk chart request per hari.
    
    Default 7 hari terakhir.
    """
    data = db_service.get_requests_by_date(days)
    
    # Generate labels untuk semua hari (termasuk yang kosong)
    labels = []
    successful = []
    failed = []
    
    # Buat dict dari data yang ada
    data_dict = {d["date"]: d for d in data}
    
    # Generate semua tanggal
    for i in range(days - 1, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(date)
        
        if date in data_dict:
            successful.append(data_dict[date]["successful"] or 0)
            failed.append(data_dict[date]["failed"] or 0)
        else:
            successful.append(0)
            failed.append(0)
    
    return RequestsChartData(
        labels=labels,
        successful=successful,
        failed=failed
    )


@router.get("/dashboard/audit-summary", response_model=AuditSummaryResponse)
async def get_audit_summary(admin_key: str = Depends(cek_akses_admin)):
    """
    Mengambil summary audit logs untuk dashboard.
    """
    stats = audit_logger.get_stats()
    recent = audit_logger.get_logs(limit=10)
    
    # Convert stats ke list of AuditEventCount
    events_by_type = [
        AuditEventCount(event_type=k, count=v)
        for k, v in stats.items()
        if k != "total"
    ]
    
    return AuditSummaryResponse(
        total_events=stats.get("total", 0),
        events_by_type=events_by_type,
        recent_events=recent
    )

