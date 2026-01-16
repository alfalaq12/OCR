"""
Router untuk export/import learned words via API.
Memerlukan admin access untuk operasi export/import.

Security Features:
- Import limits (max 10,000 words per request)
- Input validation (regex pattern for valid words)
- Audit logging for all sensitive operations
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
import re

from app.services.learning_service import learning_service
from app.services.db_service import db_service
from app.services.audit_logger import audit_logger
from app.config import settings


router = APIRouter(prefix="/api/learning", tags=["Learning Dictionary"])


# === Security Constants ===
MAX_IMPORT_WORDS = 10000  # Maksimal kata per request
MAX_WORD_LENGTH = 50      # Maksimal panjang kata
MIN_WORD_LENGTH = 2       # Minimal panjang kata
VALID_WORD_PATTERN = re.compile(r"^[a-zA-Z\-']+$")  # Hanya huruf, dash, apostrophe


# === Pydantic Models ===

class WordEntry(BaseModel):
    word: str
    frequency: int = 1
    is_approved: bool = True
    
    @field_validator('word')
    @classmethod
    def validate_word(cls, v):
        v = v.strip().lower()
        if len(v) < MIN_WORD_LENGTH:
            raise ValueError(f'Word too short (min {MIN_WORD_LENGTH} chars)')
        if len(v) > MAX_WORD_LENGTH:
            raise ValueError(f'Word too long (max {MAX_WORD_LENGTH} chars)')
        if not VALID_WORD_PATTERN.match(v):
            raise ValueError('Word contains invalid characters (only letters, dash, apostrophe allowed)')
        return v
    
    @field_validator('frequency')
    @classmethod
    def validate_frequency(cls, v):
        if v < 1:
            return 1
        if v > 1000:
            return 1000  # Cap frequency
        return v


class ExportResponse(BaseModel):
    version: str = "1.0"
    export_date: str
    total_words: int
    approved_words: List[dict]
    pending_words: List[dict]


class ImportRequest(BaseModel):
    words: List[WordEntry]
    mode: str = "merge"  # merge, replace, approved_only
    
    @field_validator('words')
    @classmethod
    def validate_words_limit(cls, v):
        if len(v) > MAX_IMPORT_WORDS:
            raise ValueError(f'Too many words ({len(v)}). Maximum allowed: {MAX_IMPORT_WORDS}')
        return v
    
    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        allowed = ['merge', 'replace', 'approved_only']
        if v not in allowed:
            raise ValueError(f'Invalid mode. Allowed: {allowed}')
        return v


class ImportResponse(BaseModel):
    success: bool
    imported: int
    skipped: int
    rejected: int
    message: str


class StatsResponse(BaseModel):
    total_tracked: int
    approved: int
    pending: int
    threshold: int


# === Helper Functions ===

def get_client_ip(request: Request) -> str:
    """Get real client IP (handle proxy/load balancer)"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_actor_identifier(admin_key: str) -> str:
    """Get actor identifier for audit log"""
    if admin_key == "master":
        return "master-key"
    return admin_key[:20] + "..." if len(admin_key) > 20 else admin_key


# === Auth Dependency ===

def cek_akses_admin(
    request: Request,
    x_admin_key: Optional[str] = Header(None, description="Admin key untuk akses")
):
    """Verifikasi akses admin dengan audit logging untuk failed attempts."""
    if not x_admin_key:
        # Log failed auth attempt
        audit_logger.log(
            event_type=audit_logger.EVENT_AUTH_FAILED,
            ip_address=get_client_ip(request),
            details={"reason": "missing_admin_key", "endpoint": str(request.url.path)}
        )
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
    
    # Log failed auth attempt
    audit_logger.log(
        event_type=audit_logger.EVENT_AUTH_FAILED,
        ip_address=get_client_ip(request),
        details={"reason": "invalid_admin_key", "endpoint": str(request.url.path)}
    )
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Admin key tidak valid",
            "error_code": "ADMIN_KEY_INVALID",
            "details": "Key yang diberikan tidak valid atau bukan admin"
        }
    )


# === Endpoints ===

@router.get("/stats", response_model=StatsResponse)
async def get_learning_stats(admin_key: str = Depends(cek_akses_admin)):
    """
    Ambil statistik learned words.
    
    Menampilkan total kata yang di-track, approved, pending, dan threshold.
    """
    stats = learning_service.get_stats()
    return StatsResponse(**stats)


@router.get("/export", response_model=ExportResponse)
async def export_learned_words(
    request: Request,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Export semua learned words ke format JSON.
    
    Format export bisa langsung digunakan untuk import di server lain.
    Include approved words dan pending words.
    """
    approved = learning_service.get_approved_words()
    pending = learning_service.get_pending_words(limit=1000)
    
    # Audit log
    audit_logger.log(
        event_type=audit_logger.EVENT_WORDS_EXPORTED,
        actor=get_actor_identifier(admin_key),
        ip_address=get_client_ip(request),
        details={
            "approved_count": len(approved),
            "pending_count": len(pending),
            "export_type": "full"
        }
    )
    
    return ExportResponse(
        version="1.0",
        export_date=datetime.now().isoformat(),
        total_words=len(approved) + len(pending),
        approved_words=approved,
        pending_words=pending
    )


@router.get("/export/approved")
async def export_approved_only(
    request: Request,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Export hanya kata-kata yang sudah di-approve.
    
    Format simple: list kata saja, bisa langsung dipakai.
    """
    approved = learning_service.get_approved_words()
    words = [w["word"] for w in approved]
    
    # Audit log
    audit_logger.log(
        event_type=audit_logger.EVENT_WORDS_EXPORTED,
        actor=get_actor_identifier(admin_key),
        ip_address=get_client_ip(request),
        details={
            "word_count": len(words),
            "export_type": "approved_only"
        }
    )
    
    return {
        "version": "1.0",
        "export_date": datetime.now().isoformat(),
        "total_words": len(words),
        "words": words
    }


@router.post("/import", response_model=ImportResponse)
async def import_learned_words(
    request_data: ImportRequest,
    request: Request,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Import learned words dari format JSON.
    
    **Security Limits:**
    - Maximum 10,000 words per request
    - Words must be 2-50 characters
    - Only letters, dash (-), and apostrophe (') allowed
    
    **Mode options:**
    - merge: Gabungkan dengan data existing (default)
    - replace: Ganti semua data, hapus yang lama
    - approved_only: Import hanya kata yang is_approved=True
    
    Request body format:
    ```json
    {
        "words": [
            {"word": "kata1", "frequency": 5, "is_approved": true},
            {"word": "kata2", "frequency": 2, "is_approved": false}
        ],
        "mode": "merge"
    }
    ```
    """
    db = db_service
    imported = 0
    skipped = 0
    rejected = 0
    
    # Mode replace: hapus semua dulu
    if request_data.mode == "replace":
        with db._konek() as conn:
            conn.execute("DELETE FROM learned_words")
            conn.commit()
    
    with db._konek() as conn:
        for entry in request_data.words:
            word_lower = entry.word  # Already validated and lowercased
            
            # Skip kalau mode approved_only dan kata belum di-approve
            if request_data.mode == "approved_only" and not entry.is_approved:
                skipped += 1
                continue
            
            try:
                # Cek apakah kata sudah ada
                cursor = conn.execute(
                    "SELECT id, frequency, is_approved FROM learned_words WHERE word = ?",
                    (word_lower,)
                )
                row = cursor.fetchone()
                
                now = datetime.now().isoformat()
                
                if row:
                    # Update: ambil frequency terbesar
                    new_freq = max(row['frequency'], entry.frequency)
                    if entry.is_approved and not row['is_approved']:
                        conn.execute("""
                            UPDATE learned_words 
                            SET frequency = ?, is_approved = 1, approved_at = ?, last_seen = ?
                            WHERE id = ?
                        """, (new_freq, now, now, row['id']))
                    else:
                        conn.execute("""
                            UPDATE learned_words 
                            SET frequency = ?, last_seen = ?
                            WHERE id = ?
                        """, (new_freq, now, row['id']))
                    imported += 1
                else:
                    # Insert baru
                    conn.execute("""
                        INSERT INTO learned_words (word, frequency, is_approved, first_seen, last_seen, approved_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        word_lower, 
                        entry.frequency, 
                        1 if entry.is_approved else 0, 
                        now, 
                        now, 
                        now if entry.is_approved else None
                    ))
                    imported += 1
            except Exception as e:
                rejected += 1
        
        conn.commit()
    
    # Refresh cache
    learning_service._refresh_cache()
    
    # Audit log
    audit_logger.log(
        event_type=audit_logger.EVENT_WORDS_IMPORTED,
        actor=get_actor_identifier(admin_key),
        ip_address=get_client_ip(request),
        details={
            "mode": request_data.mode,
            "total_submitted": len(request_data.words),
            "imported": imported,
            "skipped": skipped,
            "rejected": rejected
        }
    )
    
    return ImportResponse(
        success=True,
        imported=imported,
        skipped=skipped,
        rejected=rejected,
        message=f"Import selesai dengan mode '{request_data.mode}'"
    )


@router.post("/import/simple")
async def import_simple_wordlist(
    words: List[str],
    request: Request,
    auto_approve: bool = True,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Import simple word list (array of strings).
    
    **Security Limits:**
    - Maximum 10,000 words per request
    - Invalid words will be skipped
    
    Cocok untuk import dari file text atau list kata biasa.
    
    Request body format:
    ```json
    ["kata1", "kata2", "kata3"]
    ```
    
    Query params:
    - auto_approve: Set True untuk langsung approve semua kata (default: True)
    """
    # Limit check
    if len(words) > MAX_IMPORT_WORDS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Too many words ({len(words)})",
                "error_code": "IMPORT_LIMIT_EXCEEDED",
                "details": f"Maximum allowed: {MAX_IMPORT_WORDS} words per request"
            }
        )
    
    # Validate and filter words
    valid_entries = []
    for w in words:
        w = w.strip().lower()
        if (MIN_WORD_LENGTH <= len(w) <= MAX_WORD_LENGTH and 
            VALID_WORD_PATTERN.match(w)):
            valid_entries.append(WordEntry(word=w, frequency=5, is_approved=auto_approve))
    
    # Reuse import logic
    import_request = ImportRequest(words=valid_entries, mode="merge")
    return await import_learned_words(import_request, request, admin_key)


@router.get("/pending")
async def get_pending_words(
    limit: int = 50,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Ambil kata-kata yang belum di-approve (pending review).
    """
    # Limit the limit
    if limit > 500:
        limit = 500
    
    pending = learning_service.get_pending_words(limit=limit)
    return {
        "total": len(pending),
        "words": pending
    }


@router.post("/approve/{word}")
async def approve_word(
    word: str,
    request: Request,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Approve kata secara manual.
    """
    success = learning_service.approve_word(word)
    if success:
        # Audit log
        audit_logger.log(
            event_type=audit_logger.EVENT_WORD_APPROVED,
            actor=get_actor_identifier(admin_key),
            ip_address=get_client_ip(request),
            details={"word": word}
        )
        return {"success": True, "message": f"Kata '{word}' berhasil di-approve"}
    else:
        raise HTTPException(
            status_code=404,
            detail={"error": "Kata tidak ditemukan atau sudah di-approve"}
        )


@router.delete("/reject/{word}")
async def reject_word(
    word: str,
    request: Request,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Hapus kata dari tracking (reject).
    """
    success = learning_service.reject_word(word)
    if success:
        # Audit log
        audit_logger.log(
            event_type=audit_logger.EVENT_WORD_REJECTED,
            actor=get_actor_identifier(admin_key),
            ip_address=get_client_ip(request),
            details={"word": word}
        )
        return {"success": True, "message": f"Kata '{word}' berhasil dihapus"}
    else:
        raise HTTPException(
            status_code=404,
            detail={"error": "Kata tidak ditemukan"}
        )


@router.get("/audit-logs")
async def get_audit_logs(
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin_key: str = Depends(cek_akses_admin)
):
    """
    Ambil audit logs untuk monitoring dan compliance.
    
    Query params:
    - event_type: Filter by event type (optional)
    - limit: Maximum records to return (default: 100, max: 500)
    - offset: Pagination offset (default: 0)
    """
    # Limit the limit
    if limit > 500:
        limit = 500
    
    logs = audit_logger.get_logs(event_type=event_type, limit=limit, offset=offset)
    stats = audit_logger.get_stats()
    
    return {
        "total": stats.get('total', 0),
        "logs": logs,
        "stats": stats
    }
