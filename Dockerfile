# Codex20 Bot v2.2 - Enhanced D&D Assistant
# Container-based deployment with owner privileges and API proxy

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create data directory with proper permissions
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Expose port (optional, for health checks)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/sessions.db').execute('SELECT 1')" || exit 1

# Run the bot
CMD ["python", "bot.py"]
