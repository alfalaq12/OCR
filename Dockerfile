FROM python:3.11-slim-bookworm

# Install Tesseract OCR + poppler untuk PDF conversion
# Build time: ~1-2 menit (vs ~10 menit dengan PaddleOCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ind \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dan install requirements (lightweight, tanpa PaddleOCR)
COPY requirements.docker.light.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.light.txt

# Copy source code
COPY . .

EXPOSE 8000

# Force pakai Tesseract (PaddleOCR nggak di-install)
ENV OCR_ENGINE=tesseract

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
