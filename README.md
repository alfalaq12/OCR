# OCR API

API untuk extract text dari dokumen scan (image/PDF) dengan fitur auto-learn dictionary dan security enterprise-grade.

## Features

- ✅ Extract text dari image (PNG, JPG, JPEG, GIF, BMP, TIFF)
- ✅ Extract text dari PDF (multi-page support)
- ✅ Support bahasa Indonesia dan English
- ✅ Upload file langsung atau dari MinIO
- ✅ API Key authentication & management
- ✅ Rate limiting (30 req/min default)
- ✅ Request history & statistics
- ✅ **Auto-Learn Dictionary** - kata baru otomatis masuk kamus
- ✅ **Export/Import Learned Words** - transfer data via API
- ✅ **Audit Logging** - tracking aksi sensitif untuk compliance
- ✅ **Input Validation** - proteksi terhadap invalid data
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

# Edit .env sesuai kebutuhan (WAJIB untuk production!)

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
| GET | `/api/ocr/engines` | Lihat OCR engines tersedia |

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/keys` | Generate API key baru |
| GET | `/api/admin/keys` | List semua API keys |
| DELETE | `/api/admin/keys/{id}` | Revoke API key |
| GET | `/api/admin/keys/stats` | API key statistics |

### Learning Dictionary Endpoints (NEW!)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/learning/stats` | Statistik learned words |
| GET | `/api/learning/export` | Export semua words (JSON) |
| GET | `/api/learning/export/approved` | Export approved words only |
| POST | `/api/learning/import` | Import words (merge/replace) |
| POST | `/api/learning/import/simple` | Import simple word list |
| GET | `/api/learning/pending` | Lihat kata pending approval |
| POST | `/api/learning/approve/{word}` | Approve kata manual |
| DELETE | `/api/learning/reject/{word}` | Reject/hapus kata |
| GET | `/api/learning/audit-logs` | Lihat audit logs |

---

## Usage Examples

### Upload File (curl)

```bash
curl -X POST "http://localhost:8000/api/ocr/extract" \
  -H "X-API-Key: your-api-key" \
  -F "file=@document.pdf" \
  -F "language=mixed" \
  -F "use_dictionary=true"
```

### Generate API Key

```bash
curl -X POST "http://localhost:8000/api/admin/keys" \
  -H "X-Admin-Key: YOUR_ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Client ABC", "is_admin": false}'
```

### Export Learned Words

```bash
curl -X GET "http://localhost:8000/api/learning/export" \
  -H "X-Admin-Key: YOUR_ADMIN_MASTER_KEY"
```

### Import Learned Words

```bash
curl -X POST "http://localhost:8000/api/learning/import" \
  -H "X-Admin-Key: YOUR_ADMIN_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "words": [
      {"word": "kata1", "frequency": 5, "is_approved": true},
      {"word": "kata2", "frequency": 2, "is_approved": false}
    ],
    "mode": "merge"
  }'
```

**Import Modes:**
- `merge` - Gabungkan dengan data existing (default)
- `replace` - Hapus semua data lama, ganti dengan yang baru
- `approved_only` - Import hanya kata yang approved

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

## Security Features

### 🔐 For Production Deployment

> ⚠️ **IMPORTANT**: Sebelum deploy ke production, WAJIB:

1. **Enable API Authentication**
   ```
   API_KEYS_ENABLED=true
   ```

2. **Generate Admin Master Key yang kuat**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   
3. **Update `.env`**
   ```
   ADMIN_MASTER_KEY=<hasil generate di atas>
   ```

4. **Jangan commit `.env` ke Git!**
   ```gitignore
   # .gitignore
   .env
   .env.production
   ```

### Security Protections

| Feature | Description |
|---------|-------------|
| **API Key Hashing** | Keys di-hash dengan SHA256 sebelum disimpan |
| **Rate Limiting** | Mencegah abuse (30 req/min default) |
| **Import Limits** | Max 10,000 words per import request |
| **Input Validation** | Regex validation untuk semua input |
| **Audit Logging** | Track semua aksi sensitif untuk compliance |
| **Failed Auth Tracking** | Log semua percobaan login gagal |

---

## Error Codes

Semua error response include `error_code` untuk debugging:

| Code | Description |
|------|-------------|
| `AUTH_MISSING_KEY` | API key not provided |
| `AUTH_INVALID_KEY` | Invalid API key |
| `ADMIN_KEY_REQUIRED` | Admin key not provided |
| `ADMIN_KEY_INVALID` | Invalid admin key |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `FILE_TYPE_NOT_ALLOWED` | Unsupported file format |
| `FILE_TOO_LARGE` | File exceeds 50MB limit |
| `FILE_EMPTY` | Empty file uploaded |
| `IMPORT_LIMIT_EXCEEDED` | Too many words in import |
| `OCR_ENGINE_ERROR` | Tesseract processing failed |
| `PDF_CONVERSION_ERROR` | Failed to convert PDF |
| `MINIO_OBJECT_NOT_FOUND` | File not found in MinIO |

---

## Configuration

Edit file `.env` untuk konfigurasi:

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEYS_ENABLED` | false | Enable API key auth **(set true untuk prod!)** |
| `ADMIN_MASTER_KEY` | - | Master key untuk admin endpoints |
| `RATE_LIMIT_ENABLED` | true | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 30 | Max requests per minute |
| `PDF_DPI` | 150 | DPI untuk konversi PDF (150=cepat, 300=akurat) |
| `MINIO_ENDPOINT` | localhost:9000 | MinIO server |
| `MINIO_ACCESS_KEY` | minioadmin | MinIO access key |
| `MINIO_SECRET_KEY` | minioadmin | MinIO secret key |

---

## Auto-Learn Dictionary

Sistem secara otomatis:
1. **Track** kata-kata yang tidak dikenali saat OCR
2. **Count** frekuensi kemunculan setiap kata
3. **Auto-approve** kata yang muncul ≥5 kali
4. **Add to dictionary** kata yang sudah approved

### Manage via API

```bash
# Lihat kata pending approval
curl -H "X-Admin-Key: KEY" http://localhost:8000/api/learning/pending

# Approve kata manual
curl -X POST -H "X-Admin-Key: KEY" http://localhost:8000/api/learning/approve/kata

# Export untuk backup
curl -H "X-Admin-Key: KEY" http://localhost:8000/api/learning/export > backup.json

# Import dari backup
curl -X POST -H "X-Admin-Key: KEY" -H "Content-Type: application/json" \
  -d @backup.json http://localhost:8000/api/learning/import
```

---

## Audit Logging

Semua aksi sensitif tercatat untuk compliance:

| Event Type | Description |
|------------|-------------|
| `API_KEY_CREATED` | API key baru dibuat |
| `API_KEY_REVOKED` | API key di-revoke |
| `WORDS_IMPORTED` | Words di-import |
| `WORDS_EXPORTED` | Words di-export |
| `WORD_APPROVED` | Kata di-approve manual |
| `WORD_REJECTED` | Kata di-reject |
| `AUTH_FAILED` | Percobaan login gagal |

### View Logs

```bash
curl -H "X-Admin-Key: KEY" http://localhost:8000/api/learning/audit-logs
```

---

## License

MIT
