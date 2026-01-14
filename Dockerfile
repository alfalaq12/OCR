FROM python:3.11-slim-bookworm

# Install dependencies untuk PaddleOCR + Tesseract + pdf2image
# Build time: ~8-10 menit (download PaddleOCR models)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (termasuk PaddleOCR)
COPY requirements.docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.txt

# Copy source code
COPY . .

EXPOSE 8000

# Dual engine: tesseract (cepat) + paddle (akurat)
ENV OCR_ENGINE=auto

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
