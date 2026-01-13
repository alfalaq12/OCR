FROM python:3.11-alpine

# Install dependencies sistem via apk (sangat cepat)
RUN apk add --no-cache \
    poppler-utils \
    mesa-gl \
    libgomp \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev

WORKDIR /app

# Copy requirements dulu biar cache-nya optimal
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy semua source code
COPY . .

# Expose port
EXPOSE 8000

# Jalanin server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
