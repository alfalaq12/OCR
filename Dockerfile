FROM almalinux:9-minimal

# Install Python 3.11 dan dependencies sistem
RUN microdnf install -y \
    python3.11 \
    python3.11-pip \
    poppler-utils \
    mesa-libGL \
    libgomp \
    && microdnf clean all

# Set Python 3.11 sebagai default
RUN alternatives --set python3 /usr/bin/python3.11

WORKDIR /app

# Copy requirements dulu biar cache-nya optimal
COPY requirements.docker.txt .
RUN pip3.11 install --no-cache-dir -r requirements.docker.txt

# Copy semua source code
COPY . .

# Expose port
EXPOSE 8000

# Jalanin server
CMD ["python3.11", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
