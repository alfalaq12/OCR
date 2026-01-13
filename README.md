# OCR API

API untuk extract text dari dokumen scan (image/PDF) menggunakan Tesseract OCR.

## Features

- ✅ Extract text dari image (PNG, JPG, JPEG, GIF, BMP, TIFF)
- ✅ Extract text dari PDF (multi-page support)
- ✅ Support bahasa Indonesia dan English
- ✅ Upload file langsung atau dari MinIO
- ✅ API Key authentication
- ✅ Rate limiting (30 req/min default)
- ✅ Request history & statistics
- ✅ Detailed error codes untuk debugging
- ✅ Docker ready

## Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Tesseract OCR** - Download dari [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - Install ke `C:\Program Files\Tesseract-OCR`
   - Centang "Additional language data" → Indonesian
3. **Poppler** (untuk PDF) - Download dan extract ke `C:\poppler`, add `C:\poppler\bin` ke PATH

### Development (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run server
python -m uvicorn app.main:app --reload
```

Open API docs: http://localhost:8000/docs

### Production (Docker)

```bash
docker-compose up -d
```

## API Endpoints

### OCR Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ocr/extract` | Upload file untuk OCR |
| POST | `/api/ocr/extract-from-minio` | OCR dari file MinIO |
| GET | `/api/ocr/history` | Lihat history requests |
| GET | `/api/ocr/stats` | Lihat statistics |

### Upload File (curl)

```bash
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf" \
  -F "language=mixed"
```

### Response Format

```json
{
  "success": true,
  "text": "Extracted text content...",
  "pages": 1,
  "language": "mixed",
  "processing_time_ms": 1234,
  "error": null,
  "error_code": null
}
```

## Error Codes

Semua error response include `error_code` untuk debugging:

| Code | Description |
|------|-------------|
| `AUTH_MISSING_KEY` | API key not provided |
| `AUTH_INVALID_KEY` | Invalid API key |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `FILE_TYPE_NOT_ALLOWED` | Unsupported file format |
| `FILE_TOO_LARGE` | File exceeds 50MB limit |
| `FILE_EMPTY` | Empty file uploaded |
| `OCR_ENGINE_ERROR` | Tesseract processing failed |
| `PDF_CONVERSION_ERROR` | Failed to convert PDF |
| `MINIO_OBJECT_NOT_FOUND` | File not found in MinIO |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEYS_ENABLED` | false | Enable API key auth |
| `API_KEYS` | - | Comma-separated API keys |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 30 | Max requests per minute |
| `MINIO_ENDPOINT` | localhost:9000 | MinIO server |
| `MINIO_ACCESS_KEY` | minioadmin | MinIO access key |
| `MINIO_SECRET_KEY` | minioadmin | MinIO secret key |
