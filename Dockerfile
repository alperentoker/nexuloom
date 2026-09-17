FROM python:3.11-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

# Install system packages (build tools, libraries, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure persistent data and report folders exist
RUN mkdir -p data logs reports/exports reports/scheduled

# Make CLI tools executable and link globally in container
RUN chmod +x main.py nexuloom.py udi.py setup.sh 2>/dev/null || true && \
    ln -sf /app/nexuloom.py /usr/local/bin/nexuloom && \
    ln -sf /app/udi.py /usr/local/bin/udi

# Expose default web application port
EXPOSE 8001

# Container healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/api/health || exit 1

# Default command runs the dashboard with auto-reload
CMD ["python", "main.py"]
