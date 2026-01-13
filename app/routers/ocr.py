from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from app.models.schemas import OCRResponse, MinioOCRRequest, OCRHistoryResponse, OCRHistoryItem
from app.models.error_codes import OCRErrorCode
from app.services.ocr_service import ocr_service
from app.services.minio_service import minio_service
from app.services.db_service import db_service
from app.middleware.auth import verify_api_key
from app.config import settings
from datetime import datetime

router = APIRouter(prefix="/api/ocr", tags=["OCR"])


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_EXTENSIONS


@router.post("/extract", response_model=OCRResponse)
async def extract_text(
    file: UploadFile = File(...),
    language: str = Form(default="mixed"),
    api_key: str = Depends(verify_api_key)
):
    """
    Extract text from uploaded image or PDF file.

    - **file**: Image (PNG, JPG, etc.) or PDF file
    - **language**: Language hint - 'id' (Indonesian), 'en' (English), or 'mixed' (default)
    
    **Error Codes:**
    - FILE_TYPE_NOT_ALLOWED: Unsupported file format
    - FILE_TOO_LARGE: File exceeds 50MB limit
    - OCR_ENGINE_ERROR: OCR processing failed
    - PDF_CONVERSION_ERROR: Failed to convert PDF
    """
    # Validate file extension
    if not validate_file_extension(file.filename):
        error_msg = f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        db_service.log_request(
            filename=file.filename,
            file_size=0,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=error_msg,
            error_code=OCRErrorCode.FILE_TYPE_NOT_ALLOWED,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": error_msg,
                "error_code": OCRErrorCode.FILE_TYPE_NOT_ALLOWED
            }
        )

    # Read file content
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # Check empty file
    if file_size == 0:
        db_service.log_request(
            filename=file.filename,
            file_size=0,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message="File is empty",
            error_code=OCRErrorCode.FILE_EMPTY,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "File is empty",
                "error_code": OCRErrorCode.FILE_EMPTY
            }
        )

    # Check file size
    if file_size > settings.MAX_FILE_SIZE:
        error_msg = f"File too large. Maximum: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        db_service.log_request(
            filename=file.filename,
            file_size=file_size,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=error_msg,
            error_code=OCRErrorCode.FILE_TOO_LARGE,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": error_msg,
                "error_code": OCRErrorCode.FILE_TOO_LARGE
            }
        )

    try:
        # Process OCR
        text, pages, processing_time = ocr_service.extract_text_from_bytes(
            file_bytes,
            file.filename,
            language
        )

        # Log successful request
        db_service.log_request(
            filename=file.filename,
            file_size=file_size,
            pages=pages,
            language=language,
            processing_time_ms=processing_time,
            success=True,
            text_preview=text,
            api_key=api_key
        )

        return OCRResponse(
            success=True,
            text=text,
            pages=pages,
            language=language,
            processing_time_ms=processing_time
        )

    except Exception as e:
        error_str = str(e)
        
        # Determine error code based on exception
        if "pdf" in error_str.lower() or "poppler" in error_str.lower():
            error_code = OCRErrorCode.PDF_CONVERSION_ERROR
        elif "tesseract" in error_str.lower():
            error_code = OCRErrorCode.OCR_ENGINE_ERROR
        else:
            error_code = OCRErrorCode.INTERNAL_ERROR

        # Log failed request
        db_service.log_request(
            filename=file.filename,
            file_size=file_size,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=error_str,
            error_code=error_code,
            api_key=api_key
        )

        return OCRResponse(
            success=False,
            text="",
            pages=0,
            language=language,
            processing_time_ms=0,
            error=error_str,
            error_code=error_code
        )


@router.post("/extract-from-minio", response_model=OCRResponse)
async def extract_text_from_minio(
    request: MinioOCRRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Extract text from file stored in MinIO.

    - **bucket**: MinIO bucket name
    - **object_key**: Object key/path in the bucket
    - **language**: Language hint - 'id', 'en', or 'mixed' (default)
    
    **Error Codes:**
    - MINIO_OBJECT_NOT_FOUND: File not found in MinIO
    - MINIO_CONNECTION_ERROR: Cannot connect to MinIO
    """
    object_path = f"{request.bucket}/{request.object_key}"
    
    # Validate file extension
    if not validate_file_extension(request.object_key):
        error_msg = f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        db_service.log_request(
            filename=object_path,
            file_size=0,
            pages=0,
            language=request.language,
            processing_time_ms=0,
            success=False,
            error_message=error_msg,
            error_code=OCRErrorCode.FILE_TYPE_NOT_ALLOWED,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": error_msg,
                "error_code": OCRErrorCode.FILE_TYPE_NOT_ALLOWED
            }
        )

    try:
        # Check if object exists
        if not minio_service.check_object_exists(request.bucket, request.object_key):
            db_service.log_request(
                filename=object_path,
                file_size=0,
                pages=0,
                language=request.language,
                processing_time_ms=0,
                success=False,
                error_message=f"Object not found: {object_path}",
                error_code=OCRErrorCode.MINIO_OBJECT_NOT_FOUND,
                api_key=api_key
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": f"Object not found: {object_path}",
                    "error_code": OCRErrorCode.MINIO_OBJECT_NOT_FOUND
                }
            )

        # Get file from MinIO
        file_bytes = minio_service.get_object_bytes(request.bucket, request.object_key)
        file_size = len(file_bytes)

        # Process OCR
        text, pages, processing_time = ocr_service.extract_text_from_bytes(
            file_bytes,
            request.object_key,
            request.language
        )

        # Log successful request
        db_service.log_request(
            filename=object_path,
            file_size=file_size,
            pages=pages,
            language=request.language,
            processing_time_ms=processing_time,
            success=True,
            text_preview=text,
            api_key=api_key
        )

        return OCRResponse(
            success=True,
            text=text,
            pages=pages,
            language=request.language,
            processing_time_ms=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        error_code = OCRErrorCode.INTERNAL_ERROR
        
        if "minio" in error_str.lower() or "s3" in error_str.lower():
            error_code = OCRErrorCode.MINIO_CONNECTION_ERROR

        db_service.log_request(
            filename=object_path,
            file_size=0,
            pages=0,
            language=request.language,
            processing_time_ms=0,
            success=False,
            error_message=error_str,
            error_code=error_code,
            api_key=api_key
        )

        return OCRResponse(
            success=False,
            text="",
            pages=0,
            language=request.language,
            processing_time_ms=0,
            error=error_str,
            error_code=error_code
        )


@router.get("/history", response_model=OCRHistoryResponse)
async def get_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    api_key: str = Depends(verify_api_key)
):
    """
    Get OCR request history with pagination.
    
    - **limit**: Number of records to return (1-100, default: 50)
    - **offset**: Number of records to skip (default: 0)
    """
    items = db_service.get_history(limit=limit, offset=offset)
    total = db_service.get_total_count()
    
    return OCRHistoryResponse(
        total=total,
        items=[
            OCRHistoryItem(
                id=item["id"],
                filename=item["filename"],
                file_size=item["file_size"],
                pages=item["pages"],
                language=item["language"],
                processing_time_ms=item["processing_time_ms"],
                success=bool(item["success"]),
                error_message=item["error_message"],
                created_at=datetime.fromisoformat(item["created_at"]) if item["created_at"] else datetime.now()
            )
            for item in items
        ]
    )


@router.get("/stats")
async def get_stats(api_key: str = Depends(verify_api_key)):
    """
    Get OCR usage statistics.
    
    Returns total requests, success/fail counts, average processing time.
    """
    return db_service.get_stats()
