# CI Failure Agent - Production Docker Image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create .env file placeholder
RUN echo "GOOGLE_API_KEY=" > .env

# Health check (disabled during startup to allow gradual initialization)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
