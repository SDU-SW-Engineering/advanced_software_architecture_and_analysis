FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kafka_collector.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "kafka_collector.py"]