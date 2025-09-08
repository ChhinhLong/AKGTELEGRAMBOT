# Professional Telegram YouTube Downloader Bot - Production Dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="AKG Technology <chhinhlong2008@gmail.com>"
LABEL version="2.0.0"
LABEL description="Professional Telegram YouTube Downloader Bot with Enterprise Features"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    ca-certificates \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper structure
RUN mkdir -p logs temp db cookies deploy \
    && mkdir -p utils \
    && mkdir -p bot

# Set proper permissions
RUN chown -R appuser:appuser /app \
    && chmod +x deploy/start.sh

# Switch to app user for security
USER appuser

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.exit(0)" || exit 1

# Optional: Expose port for health checks or web interfaces
EXPOSE 8080

# Default command
CMD ["python", "bot/main.py"]