# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy entire src directory (includes main.py)
COPY src/ ./src/

# Create volume mount points
VOLUME ["/app/collector_output", "/app/final_results"]

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the analyzer
CMD ["python", "-m", "src.main"]