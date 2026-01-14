"""
Model Pydantic buat validasi request dan response.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OCRResponse(BaseModel):
    """Format response hasil OCR"""
    success: bool
    text: str
    normalized_text: Optional[str] = None  # Teks dengan ejaan modern (jika normalize_spelling=true)
    spelling_changes: Optional[int] = None  # Jumlah kata yang dikonversi
    pages: int
    language: str
    processing_time_ms: int
    error: Optional[str] = None
    error_code: Optional[str] = None


class MinioOCRRequest(BaseModel):
    """Request buat OCR dari MinIO"""
    bucket: str
    object_key: str
    language: str = "mixed"


class HealthResponse(BaseModel):
    """Response health check"""
    status: str
    version: str


class OCRHistoryItem(BaseModel):
    """Satu item di history"""
    id: int
    filename: str
    file_size: int
    pages: int
    language: str
    processing_time_ms: int
    success: bool
    error_message: Optional[str] = None
    created_at: datetime


class OCRHistoryResponse(BaseModel):
    """Response list history"""
    total: int
    items: list[OCRHistoryItem]


class ErrorDetail(BaseModel):
    """Format error detail"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[str] = None


# Model untuk API Key management

class APIKeyCreateRequest(BaseModel):
    """Request bikin API key baru"""
    name: str
    is_admin: bool = False


class APIKeyResponse(BaseModel):
    """Response setelah bikin API key"""
    id: int
    key: str
    key_prefix: str
    name: str
    is_admin: bool
    message: str


class APIKeyInfo(BaseModel):
    """Info API key (tanpa key asli)"""
    id: int
    key_prefix: str
    name: str
    is_admin: bool
    is_active: bool
    requests_count: int
    last_used_at: Optional[str] = None
    created_at: str
    revoked_at: Optional[str] = None


class APIKeyListResponse(BaseModel):
    """Response list API keys"""
    total: int
    keys: list[APIKeyInfo]


class APIKeyStatsResponse(BaseModel):
    """Statistik API keys"""
    total_keys: int
    active_keys: int
    revoked_keys: int
    total_requests: int
