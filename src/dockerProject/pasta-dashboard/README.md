# 🍝 Pasta Production Kafka Events Dashboard

A real-time dashboard for monitoring Kafka events from the Pasta Production System, built with React and Node.js.

## 📋 Prerequisites

Before starting the dashboard, ensure the following systems are running:

### 1. **Docker Services Must Be Running**

Make sure your pasta production system is active:

```bash
# Navigate to the main docker project directory
cd ../

# Start all pasta production services
./run_experiment.sh

# OR manually start with docker-compose
docker-compose up -d
```

**Required Services:**

- ✅ **Zookeeper** (port 2181)
- ✅ **Kafka** (port 9092)
- ✅ **PostgreSQL Database** (port 5433)
- ✅ **Pasta System** (simulation engine)
- ✅ **Scheduler & Scheduler Shadow**
- ✅ **Sorting Subsystem**
- ✅ **DB Interface**
- ✅ **Kafka Monitor**

### 2. **Verify Kafka Topics Exist**

Check that all required Kafka topics are created:

```bash
# List Kafka topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Should show:
# - heartbeats
# - productionPlan
# - storageAlerts
# - batches
# - storageLevels
```

### 3. **Check Services Status**

Verify all containers are healthy:

```bash
docker-compose ps
```

## 🚀 Installation & Setup

### Install Dependencies

```bash
# Install backend dependencies
npm install

# Install React client dependencies
cd client
npm install
cd ..
```

## 🎯 Starting the Dashboard

### Option 1: Quick Start (Recommended)

```bash
./start-dashboard.sh
```

### Option 2: Manual Start

**Terminal 1 - Backend Server:**

```bash
node server/server.js
```

**Terminal 2 - React Client:**

```bash
cd client
npm start
```

## 🌐 Access Dashboard

- **Dashboard UI**: http://localhost:3000
- **Backend API**: http://localhost:3001
- **WebSocket**: ws://localhost:3001

## 📊 Dashboard Features

### Real-time Event Monitoring

- 💓 **Machine Heartbeats** - Every 5 seconds from cutting machines
- 📋 **Production Plans** - Scheduler commands and responses
- ⚠️ **Storage Alerts** - When levels go below 20% or above 80%
- 📦 **New Batches** - Pasta batch creation events

### Production Plan Events

- 🔧 **AssignBlade** - Scheduler assigns blades to machines
- 🔄 **SwapBlade** - Blade swaps during failure recovery
- 📊 **ChangeFreshAmount** - Production ratio adjustments
- ✅ **BladeSwapped** - Confirmation from cutting machines
- ✅ **FreshAmountChanged** - Confirmation from sorting subsystem

### Visual Components

- **Machine Status Cards** - Shows active machines and blade types
- **Production Statistics** - Real-time counters and metrics
- **Live Event Streams** - Four-column event display
- **Production Plan Summary** - Recent production actions
- **Connection Status** - Live connection indicator

## 🔧 Troubleshooting

### Common Issues

**1. "Cannot connect to Kafka"**

- Ensure Docker services are running: `docker-compose ps`
- Check Kafka is healthy: `docker logs kafka`
- Verify port 9092 is accessible

**2. "No events appearing"**

- Check pasta system is producing events: `docker logs dockerproject-pasta-system-1`
- Verify Kafka topics exist: `docker exec kafka kafka-topics --list --bootstrap-server localhost:9092`

**3. "WebSocket connection failed"**

- Ensure backend server is running on port 3001
- Check no other services are using port 3001
- Verify React app can reach `ws://localhost:3001`

**4. "React app won't start"**

- Run `npm install` in the `client` directory
- Check no other services are using port 3000
- Clear npm cache: `npm cache clean --force`

### Logs and Debugging

```bash
# Check specific service logs
docker logs dockerproject-pasta-system-1
docker logs kafka
docker logs dockerproject-kafka-monitor-1

# Check all container status
docker-compose ps

# Restart specific service
docker-compose restart kafka
```

## 📁 Project Structure

```
pasta-dashboard/
├── server/
│   └── server.js          # Node.js backend with Kafka consumer
├── client/                # React dashboard
│   ├── src/
│   │   ├── components/    # Dashboard components
│   │   │   ├── Dashboard.js
│   │   │   ├── EventCard.js
│   │   │   ├── MachineStatus.js
│   │   │   └── ProductionStats.js
│   │   └── hooks/
│   │       └── useWebSocket.js
├── start-dashboard.sh     # Quick start script
├── package.json          # Backend dependencies
└── README.md
```

## 🔄 Development

### Backend API Endpoints

- `GET /api/events` - All recent events
- `GET /api/events/:topic` - Events for specific topic
- `GET /api/stats` - Event statistics
- `WebSocket /` - Real-time event stream

### Environment Variables

- `PORT` - Backend server port (default: 3001)
- Kafka broker configured for `localhost:9092`

## 📝 Notes

- Dashboard keeps last 100 events per topic in memory
- WebSocket automatically reconnects on connection loss
- Production plan events have enhanced display with action descriptions
- All timestamps are shown in local browser time
- Dashboard is responsive and works on mobile devices
