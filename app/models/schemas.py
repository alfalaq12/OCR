from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OCRResponse(BaseModel):
    """Response model for OCR extraction"""
    success: bool
    text: str
    pages: int
    language: str
    processing_time_ms: int
    error: Optional[str] = None
    error_code: Optional[str] = None


class MinioOCRRequest(BaseModel):
    """Request model for MinIO-based OCR"""
    bucket: str
    object_key: str
    language: str = "mixed"


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str


class OCRHistoryItem(BaseModel):
    """History item for OCR requests"""
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
    """Response for history endpoint"""
    total: int
    items: list[OCRHistoryItem]


class ErrorDetail(BaseModel):
    """Detailed error response"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[str] = None


# ==================== API Key Models ====================

class APIKeyCreateRequest(BaseModel):
    """Request to create new API key"""
    name: str
    is_admin: bool = False


class APIKeyResponse(BaseModel):
    """Response after creating API key"""
    id: int
    key: str
    key_prefix: str
    name: str
    is_admin: bool
    message: str


class APIKeyInfo(BaseModel):
    """API key info (without actual key)"""
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
    """Response for listing API keys"""
    total: int
    keys: list[APIKeyInfo]


class APIKeyStatsResponse(BaseModel):
    """API key statistics"""
    total_keys: int
    active_keys: int
    revoked_keys: int
    total_requests: int
