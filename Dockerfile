# Codex20 OpenRouter - Docker Image
# Multi-stage build for optimal size

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/uploads

# Expose port
EXPOSE 8084

# Default command (will be overridden by docker-compose)
CMD ["python", "app.py"]
