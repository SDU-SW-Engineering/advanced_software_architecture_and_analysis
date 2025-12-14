FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY chaos_engine.py .
COPY docker_manager.py .
COPY kafka_reporter.py .
COPY redis_inspector.py .

# Create non-root user
RUN useradd -m -u 10020 appuser && chown -R appuser:appuser /app

USER appuser

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the application
CMD ["python", "main.py"]