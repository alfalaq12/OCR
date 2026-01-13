FROM python:3.11-slim-bookworm

# Install dependencies sistem yang dibutuhkan untuk PaddleOCR & pdf2image
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Jalanin server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
