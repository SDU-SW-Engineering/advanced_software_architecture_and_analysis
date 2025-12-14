FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python modules
COPY main.py .
COPY cutting_machine.py .
COPY state.py .
COPY mqtt_manager.py .
COPY message_handler.py .
COPY heartbeat.py .

# Create non-root user for security
RUN useradd -m -u 10010 appuser

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main.py"]