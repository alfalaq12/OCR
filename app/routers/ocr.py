"""Router untuk endpoint OCR.
Menangani upload file, proses ekstraksi teks, dan riwayat penggunaan.
"""

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


def cek_ekstensi_valid(nama_file: str) -> bool:
    """Cek apakah ekstensi file diperbolehkan"""
    ext = nama_file.rsplit(".", 1)[-1].lower() if "." in nama_file else ""
    return ext in settings.ALLOWED_EXTENSIONS


@router.get("/engines")
async def get_available_engines():
    """
    Lihat daftar OCR engine yang tersedia.
    
    Gunakan untuk mengetahui engine mana yang bisa dipilih saat request.
    """
    return {
        "available_engines": ocr_service.get_available_engines(),
        "default_engine": ocr_service.get_engine_name(),
        "engine_info": {
            "tesseract": "Lebih cepat, cocok untuk dokumen scan jelas",
            "paddle": "Lebih akurat, cocok untuk dokumen buram/kurang jelas"
        }
    }

@router.post("/extract", response_model=OCRResponse)
async def extract_text(
    file: UploadFile = File(..., description="File gambar atau PDF yang akan diproses"),
    language: str = Form(default="mixed", description="Bahasa dokumen: id, en, atau mixed"),
    engine: str = Form(default="auto", description="OCR engine: tesseract (cepat), paddle (akurat), atau auto"),
    enhance: bool = Form(default=False, description="Aktifkan preprocessing untuk dokumen jadul/pudar"),
    normalize_spelling: bool = Form(default=False, description="Konversi ejaan lama (oe→u, dj→j, tj→c, dll) ke ejaan modern"),
    api_key: str = Depends(verify_api_key)
):
    """
    Ekstrak teks dari file dokumen yang diupload.
    
    Mendukung format gambar (PNG, JPG, JPEG, GIF, BMP, TIFF) dan PDF multi-halaman.
    Maksimal ukuran file 50MB.
    
    Parameter language:
    - id: Bahasa Indonesia
    - en: English  
    - mixed: Deteksi otomatis (default)
    
    Parameter engine:
    - tesseract: Lebih cepat, cocok untuk dokumen scan jelas
    - paddle: Lebih akurat, cocok untuk dokumen buram/kurang jelas
    - auto: Otomatis pilih engine default (default)
    
    Parameter enhance:
    - true: Tingkatkan kontras gambar untuk dokumen jadul/pudar
    - false: Tanpa preprocessing (default)
    
    Parameter normalize_spelling:
    - true: Konversi ejaan lama Indonesia (Van Ophuijsen/Soewandi) ke EYD modern
    - false: Biarkan teks apa adanya (default)
    """
    # validasi ekstensi
    if not cek_ekstensi_valid(file.filename):
        pesan = f"Tipe file tidak didukung. Yang boleh: {settings.ALLOWED_EXTENSIONS}"
        db_service.catat_request(
            filename=file.filename,
            file_size=0,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=pesan,
            error_code=OCRErrorCode.FILE_TYPE_NOT_ALLOWED,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": pesan,
                "error_code": OCRErrorCode.FILE_TYPE_NOT_ALLOWED
            }
        )

    # baca isi file
    isi_file = await file.read()
    ukuran_file = len(isi_file)

    # cek file kosong
    if ukuran_file == 0:
        db_service.catat_request(
            filename=file.filename,
            file_size=0,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message="File kosong",
            error_code=OCRErrorCode.FILE_EMPTY,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "File kosong",
                "error_code": OCRErrorCode.FILE_EMPTY
            }
        )

    # cek ukuran file
    if ukuran_file > settings.MAX_FILE_SIZE:
        pesan = f"File terlalu besar. Maksimal: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        db_service.catat_request(
            filename=file.filename,
            file_size=ukuran_file,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=pesan,
            error_code=OCRErrorCode.FILE_TOO_LARGE,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": pesan,
                "error_code": OCRErrorCode.FILE_TOO_LARGE
            }
        )

    try:
        # proses OCR dengan engine yang dipilih
        text, halaman, waktu_proses = ocr_service.proses_file(
            isi_file,
            file.filename,
            language,
            engine,
            enhance
        )

        # Normalisasi ejaan lama jika diminta
        normalized_text = None
        spelling_changes = None
        if normalize_spelling and text:
            from app.services.spelling_normalizer import normalize_with_comparison
            _, normalized_text, spelling_changes = normalize_with_comparison(text)

        # catat ke history
        db_service.catat_request(
            filename=file.filename,
            file_size=ukuran_file,
            pages=halaman,
            language=language,
            processing_time_ms=waktu_proses,
            success=True,
            text_preview=text,
            api_key=api_key
        )

        return OCRResponse(
            success=True,
            text=text,
            normalized_text=normalized_text,
            spelling_changes=spelling_changes,
            pages=halaman,
            language=language,
            processing_time_ms=waktu_proses
        )

    except Exception as e:
        pesan_error = str(e)
        
        # tentuin error code berdasarkan pesan error
        if "pdf" in pesan_error.lower() or "poppler" in pesan_error.lower():
            kode_error = OCRErrorCode.PDF_CONVERSION_ERROR
        elif "tesseract" in pesan_error.lower():
            kode_error = OCRErrorCode.OCR_ENGINE_ERROR
        else:
            kode_error = OCRErrorCode.INTERNAL_ERROR

        # catat error
        db_service.catat_request(
            filename=file.filename,
            file_size=ukuran_file,
            pages=0,
            language=language,
            processing_time_ms=0,
            success=False,
            error_message=pesan_error,
            error_code=kode_error,
            api_key=api_key
        )

        return OCRResponse(
            success=False,
            text="",
            pages=0,
            language=language,
            processing_time_ms=0,
            error=pesan_error,
            error_code=kode_error
        )


@router.post("/extract-from-minio", response_model=OCRResponse)
async def extract_from_minio(
    request: MinioOCRRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Ekstrak teks dari file yang tersimpan di MinIO object storage.
    
    Gunakan endpoint ini untuk memproses file yang sudah ada di storage
    tanpa perlu upload ulang.
    """
    path_lengkap = f"{request.bucket}/{request.object_key}"
    
    # validasi ekstensi
    if not cek_ekstensi_valid(request.object_key):
        pesan = f"Tipe file tidak didukung. Yang boleh: {settings.ALLOWED_EXTENSIONS}"
        db_service.catat_request(
            filename=path_lengkap,
            file_size=0,
            pages=0,
            language=request.language,
            processing_time_ms=0,
            success=False,
            error_message=pesan,
            error_code=OCRErrorCode.FILE_TYPE_NOT_ALLOWED,
            api_key=api_key
        )
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": pesan,
                "error_code": OCRErrorCode.FILE_TYPE_NOT_ALLOWED
            }
        )

    try:
        # cek file ada atau tidak
        if not minio_service.cek_file_ada(request.bucket, request.object_key):
            db_service.catat_request(
                filename=path_lengkap,
                file_size=0,
                pages=0,
                language=request.language,
                processing_time_ms=0,
                success=False,
                error_message=f"File tidak ditemukan: {path_lengkap}",
                error_code=OCRErrorCode.MINIO_OBJECT_NOT_FOUND,
                api_key=api_key
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": f"File tidak ditemukan: {path_lengkap}",
                    "error_code": OCRErrorCode.MINIO_OBJECT_NOT_FOUND
                }
            )

        # ambil file dari MinIO
        isi_file = minio_service.ambil_file(request.bucket, request.object_key)
        ukuran_file = len(isi_file)

        # proses OCR
        text, halaman, waktu_proses = ocr_service.proses_file(
            isi_file,
            request.object_key,
            request.language
        )

        # catat ke history
        db_service.catat_request(
            filename=path_lengkap,
            file_size=ukuran_file,
            pages=halaman,
            language=request.language,
            processing_time_ms=waktu_proses,
            success=True,
            text_preview=text,
            api_key=api_key
        )

        return OCRResponse(
            success=True,
            text=text,
            pages=halaman,
            language=request.language,
            processing_time_ms=waktu_proses
        )

    except HTTPException:
        raise
    except Exception as e:
        pesan_error = str(e)
        kode_error = OCRErrorCode.INTERNAL_ERROR
        
        if "minio" in pesan_error.lower() or "s3" in pesan_error.lower():
            kode_error = OCRErrorCode.MINIO_CONNECTION_ERROR

        db_service.catat_request(
            filename=path_lengkap,
            file_size=0,
            pages=0,
            language=request.language,
            processing_time_ms=0,
            success=False,
            error_message=pesan_error,
            error_code=kode_error,
            api_key=api_key
        )

        return OCRResponse(
            success=False,
            text="",
            pages=0,
            language=request.language,
            processing_time_ms=0,
            error=pesan_error,
            error_code=kode_error
        )


@router.get("/history", response_model=OCRHistoryResponse)
async def get_history(
    limit: int = Query(default=50, ge=1, le=100, description="Jumlah data per halaman"),
    offset: int = Query(default=0, ge=0, description="Data mulai dari index ke-"),
    api_key: str = Depends(verify_api_key)
):
    """
    Mengambil riwayat request OCR dengan pagination.
    
    Gunakan parameter limit dan offset untuk navigasi data.
    """
    items = db_service.ambil_history(limit=limit, offset=offset)
    total = db_service.hitung_total()
    
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
    Mengambil ringkasan statistik penggunaan API.
    
    Menampilkan total request, success rate, dan rata-rata waktu proses.
    """
    return db_service.ambil_stats()
