from fastapi import APIRouter, HTTPException, Depends, Header
from app.models.schemas import (
    APIKeyCreateRequest, APIKeyResponse, APIKeyInfo, 
    APIKeyListResponse, APIKeyStatsResponse
)
from app.services.db_service import db_service
from app.config import settings
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["Admin - API Key Management"])


def verify_admin_access(x_admin_key: Optional[str] = Header(None)):
    """
    Verify admin access via:
    1. Admin API key from database
    2. Master admin key from .env (ADMIN_MASTER_KEY)
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Admin key required",
                "error_code": "ADMIN_KEY_REQUIRED",
                "details": "Provide X-Admin-Key header"
            }
        )
    
    # Check master admin key from env
    if settings.ADMIN_MASTER_KEY and x_admin_key == settings.ADMIN_MASTER_KEY:
        return "master"
    
    # Check if it's an admin API key from database
    if db_service.is_admin_key(x_admin_key):
        return x_admin_key
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Invalid admin key",
            "error_code": "ADMIN_KEY_INVALID",
            "details": "The provided admin key is not valid"
        }
    )


@router.post("/keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    admin_key: str = Depends(verify_admin_access)
):
    """
    Generate a new API key.
    
    **Requires Admin Access** (X-Admin-Key header)
    
    - **name**: Descriptive name for the key (e.g., "Client Pak Faris")
    - **is_admin**: Set to true to create an admin key
    
    ⚠️ The full API key is only returned ONCE. Save it securely!
    """
    result = db_service.generate_api_key(
        name=request.name,
        is_admin=request.is_admin
    )
    
    return APIKeyResponse(**result)


@router.get("/keys", response_model=APIKeyListResponse)
async def list_api_keys(admin_key: str = Depends(verify_admin_access)):
    """
    List all API keys.
    
    **Requires Admin Access** (X-Admin-Key header)
    
    Note: Actual keys are not shown, only prefixes.
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
async def revoke_api_key(
    key_id: int,
    admin_key: str = Depends(verify_admin_access)
):
    """
    Revoke an API key.
    
    **Requires Admin Access** (X-Admin-Key header)
    
    Revoked keys cannot be used anymore.
    """
    success = db_service.revoke_api_key(key_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "API key not found",
                "error_code": "KEY_NOT_FOUND"
            }
        )
    
    return {"success": True, "message": f"API key {key_id} has been revoked"}


@router.get("/keys/stats", response_model=APIKeyStatsResponse)
async def get_api_key_stats(admin_key: str = Depends(verify_admin_access)):
    """
    Get API key statistics.
    
    **Requires Admin Access** (X-Admin-Key header)
    """
    stats = db_service.get_api_key_stats()
    return APIKeyStatsResponse(**stats)
