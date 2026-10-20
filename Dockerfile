# ==============================================================================
#  OFO-DBMS — Production Multi-Stage Dockerfile (Python 3.12 Slim)
# ==============================================================================
FROM python:3.12-slim as base

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure startup script is executable
RUN chmod +x startup.sh

# Expose web server port
EXPOSE 8000

# Default entrypoint
CMD ["/bin/bash", "startup.sh"]
