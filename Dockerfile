# Use Python 3.11 slim image for compatibility
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with timeout and retry
RUN pip install --upgrade pip && \
    pip install --timeout=300 --retries=3 -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for credentials and logs
RUN mkdir -p /app/creds /app/logs

# Health check with correct endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Expose port (Render will set PORT env var)
EXPOSE ${PORT}

# Run the application with dynamic port from Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
