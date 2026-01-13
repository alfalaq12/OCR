FROM python:3.11-slim-bookworm

# Install dependencies sistem untuk OCR engines & pdf2image
# - tesseract-ocr: engine cepat untuk dokumen jelas
# - libgl1, libglib2.0-0, dll: dependencies untuk PaddleOCR
# - poppler-utils: untuk convert PDF ke image
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

# Copy requirements dulu biar cache-nya optimal
COPY requirements.docker.txt .

# Upgrade pip dulu, lalu install requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.txt

# Copy semua source code
COPY . .

# Expose port
EXPOSE 8000

# Set default engine ke tesseract (lebih cepat)
ENV OCR_ENGINE=tesseract

# Jalanin server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
