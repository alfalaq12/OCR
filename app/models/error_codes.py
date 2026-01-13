"""
Daftar kode error buat debugging.
Setiap error ada kode unik biar gampang nyari masalahnya.
"""


class OCRErrorCode:
    # error autentikasi
    AUTH_MISSING_KEY = "AUTH_MISSING_KEY"       # gak ada API key
    AUTH_INVALID_KEY = "AUTH_INVALID_KEY"       # API key salah
    
    # error rate limit
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED" # kebanyakan request
    
    # error file
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"   # format gak didukung
    FILE_TOO_LARGE = "FILE_TOO_LARGE"                 # file kegedean
    FILE_EMPTY = "FILE_EMPTY"                         # file kosong
    FILE_CORRUPTED = "FILE_CORRUPTED"                 # file rusak
    FILE_NOT_FOUND = "FILE_NOT_FOUND"                 # file gak ketemu
    
    # error proses OCR
    OCR_ENGINE_ERROR = "OCR_ENGINE_ERROR"             # tesseract error
    OCR_NO_TEXT_FOUND = "OCR_NO_TEXT_FOUND"           # gak ada text
    OCR_LANGUAGE_NOT_SUPPORTED = "OCR_LANGUAGE_NOT_SUPPORTED"  # bahasa gak ada
    OCR_TIMEOUT = "OCR_TIMEOUT"                       # kelamaan
    
    # error PDF
    PDF_CONVERSION_ERROR = "PDF_CONVERSION_ERROR"     # gagal convert PDF
    PDF_PASSWORD_PROTECTED = "PDF_PASSWORD_PROTECTED" # PDF dikunci
    PDF_TOO_MANY_PAGES = "PDF_TOO_MANY_PAGES"        # halaman kebanyakan
    
    # error MinIO
    MINIO_CONNECTION_ERROR = "MINIO_CONNECTION_ERROR" # gak bisa konek
    MINIO_OBJECT_NOT_FOUND = "MINIO_OBJECT_NOT_FOUND" # file gak ada
    MINIO_BUCKET_NOT_FOUND = "MINIO_BUCKET_NOT_FOUND" # bucket gak ada
    
    # error umum
    INTERNAL_ERROR = "INTERNAL_ERROR"                 # error server
    UNKNOWN_ERROR = "UNKNOWN_ERROR"                   # error gak diketahui
