FROM python:3.11-slim

WORKDIR /app

# Install kafka-python
RUN pip install --no-cache-dir kafka-python

# Copy the monitor script
COPY kafka_monitor.py .

# Run the monitor
CMD ["python", "kafka_monitor.py"]