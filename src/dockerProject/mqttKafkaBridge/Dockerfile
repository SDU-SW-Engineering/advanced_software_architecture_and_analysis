FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bridge script
COPY mqtt_kafka_broker.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bridge
CMD ["python", "mqtt_kafka_broker.py"]