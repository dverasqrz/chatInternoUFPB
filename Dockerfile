FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including FFmpeg for video conversion
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app
COPY ./scripts ./scripts

# Create necessary directories
RUN mkdir -p /app/uploads /app/runtime /app/logs

# Set permissions
RUN chmod +x /app/uploads /app/runtime /app/scripts/*.py

# Make startup script executable
RUN chmod +x /app/scripts/startup_check.py

EXPOSE 8000

# Health check to verify FFmpeg is available
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/scripts/startup_check.py || exit 1

# Run startup check before starting the application
CMD ["sh", "-c", "python /app/scripts/startup_check.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
