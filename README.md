# OCR API

API untuk extract text dari dokumen scan (image/PDF) menggunakan Tesseract OCR.

## Features

- ✅ Extract text dari image (PNG, JPG, JPEG, GIF, BMP, TIFF)
- ✅ Extract text dari PDF (multi-page support)
- ✅ Support bahasa Indonesia dan English
- ✅ Upload file langsung atau dari MinIO
- ✅ API Key authentication & management
- ✅ Rate limiting (30 req/min default)
- ✅ Request history & statistics
- ✅ Detailed error codes untuk debugging
- ✅ Docker ready

---

## Quick Start

### 🐳 Docker (Recommended - All Platforms)

Cara paling gampang untuk run di **Mac, Windows, atau Linux**:

```bash
# Clone repository
git clone https://github.com/alfalaq12/OCR.git
cd OCR

# Copy environment file
cp .env.example .env

# Edit .env sesuai kebutuhan (optional)

# Run dengan Docker
docker-compose up -d
```

API ready di: **http://localhost:8000**

Swagger docs: **http://localhost:8000/docs**

---

### 🍎 macOS (Manual)

**1. Install dependencies via Homebrew:**
```bash
# Install Tesseract OCR
brew install tesseract

# Install language data (Indonesian)
brew install tesseract-lang

# Install Poppler (untuk PDF support)
brew install poppler
```

**2. Setup project:**
```bash
# Clone repository
git clone https://github.com/alfalaq12/OCR.git
cd OCR

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

**3. Run server:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

---

### 🪟 Windows (Manual)

**1. Install Tesseract OCR:**
- Download installer dari: https://github.com/UB-Mannheim/tesseract/wiki
- Pilih: `tesseract-ocr-w64-setup-5.x.x.exe`
- Saat install, centang **"Additional language data"** → pilih **Indonesian**
- Default install path: `C:\Program Files\Tesseract-OCR`

**2. Install Poppler (untuk PDF support):**
- Download dari: https://github.com/osber/poppler-windows/releases
- Extract ke `C:\poppler`
- Tambahkan `C:\poppler\bin` ke System PATH

**3. Setup project:**
```bash
# Clone repository
git clone https://github.com/alfalaq12/OCR.git
cd OCR

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env
```

**4. Run server:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

### OCR Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ocr/extract` | Upload file untuk OCR |
| POST | `/api/ocr/extract-from-minio` | OCR dari file MinIO |
| GET | `/api/ocr/history` | Lihat history requests |
| GET | `/api/ocr/stats` | Lihat statistics |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/keys` | Generate API key baru |
| GET | `/api/admin/keys` | List semua API keys |
| DELETE | `/api/admin/keys/{id}` | Revoke API key |
| GET | `/api/admin/keys/stats` | API key statistics |

---

## Usage Examples

### Upload File (curl)

```bash
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf" \
  -F "language=mixed"
```

### Generate API Key

```bash
curl -X POST "http://localhost:8000/api/admin/keys" \
  -H "X-Admin-Key: admin-master-secret-key-change-this" \
  -H "Content-Type: application/json" \
  -d '{"name": "Client Pak Faris", "is_admin": false}'
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

---

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

---

## Configuration

Edit file `.env` untuk konfigurasi:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEYS_ENABLED` | false | Enable API key auth |
| `ADMIN_MASTER_KEY` | - | Master key untuk admin endpoints |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 30 | Max requests per minute |
| `MINIO_ENDPOINT` | localhost:9000 | MinIO server |
| `MINIO_ACCESS_KEY` | minioadmin | MinIO access key |
| `MINIO_SECRET_KEY` | minioadmin | MinIO secret key |

---

## License

MIT
