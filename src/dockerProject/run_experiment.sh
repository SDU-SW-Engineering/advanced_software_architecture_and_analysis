#!/bin/bash

set -e

echo "Stopping and removing containers, networks, and volumes..."
docker-compose down -v

echo "Building Docker images..."
if ! docker-compose build; then
    echo "ERROR: Docker build failed!"
    exit 1
fi

echo "Building ChaosPanda image..."
if ! docker build -t chaospanda:latest ./chaosPanda/; then
    echo "ERROR: ChaosPanda build failed!"
    exit 1
fi

echo "Starting containers in detached mode..."
docker-compose up -d

# Wait for system to stabilize
echo "Waiting 30 seconds for system to stabilize..."
sleep 30

# Run ChaosPanda with custom parameters
echo "Starting ChaosPanda chaos testing..."

# Remove old container if it exists
docker rm -f chaospanda-experiment 2>/dev/null || true

# Fix Docker socket permissions (with proper error handling)
if [ -S /var/run/docker.sock ]; then
    sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
    ls -la /var/run/docker.sock
fi

docker run -d \
    --name chaospanda-experiment \
    --network dockerproject_mynetwork \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --group-add 0 \
    -e PYTHONUNBUFFERED=1 \
    chaospanda:latest \
    python main.py \
    --max-cutting-machines 1 \
    --max-schedulers 0 \
    --kafka-bootstrap kafka:29092 \
    --redis-host redis \
    --redis-port 6379 \
    --test-name "resilience-test-001"

echo ""
echo "=" | awk '{for(i=0;i<80;i++) printf "="; print ""}'
echo "✅ Experiment started!"
echo "=" | awk '{for(i=0;i<80;i++) printf "="; print ""}'
echo ""
echo "Monitor ChaosPanda:"
echo "  docker logs chaospanda-experiment -f"
echo ""
echo "Monitor Kafka messages:"
echo "  docker logs dockerproject-kafka-monitor-1 -f"
echo ""
echo "Stop experiment:"
echo "  docker stop chaospanda-experiment"
echo ""
echo "Cleanup:"
echo "  docker-compose down -v"
echo ""