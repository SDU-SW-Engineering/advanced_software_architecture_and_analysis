const { Kafka } = require("kafkajs");
const WebSocket = require("ws");
const express = require("express");
const cors = require("cors");
const http = require("http");

const app = express();
app.use(cors());

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Kafka configuration
const kafka = new Kafka({
  clientId: "pasta-dashboard",
  brokers: ["localhost:9092"], // Change to kafka:29092 if running in Docker
});

const consumer = kafka.consumer({ groupId: "dashboard-group" });

// Store recent events for new connections
const recentEvents = {
  heartbeats: [],
  productionPlan: [],
  storageAlerts: [],
  batches: [],
};

const MAX_EVENTS = 100; // Keep last 100 events per topic

// WebSocket connections
const clients = new Set();

// Broadcast event to all connected clients
function broadcast(data) {
  const message = JSON.stringify(data);
  clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

// Add event to recent events and broadcast
function handleEvent(topic, message) {
  const event = {
    timestamp: new Date().toISOString(),
    topic,
    data: message,
  };

  // Store in recent events
  if (!recentEvents[topic]) {
    recentEvents[topic] = [];
  }
  recentEvents[topic].push(event);

  // Keep only recent events
  if (recentEvents[topic].length > MAX_EVENTS) {
    recentEvents[topic] = recentEvents[topic].slice(-MAX_EVENTS);
  }

  // Broadcast to clients
  broadcast(event);

  console.log(`[${new Date().toISOString()}] ${topic}:`, message);
}

// Setup Kafka consumer
async function setupKafka() {
  await consumer.connect();

  // Subscribe to topics
  await consumer.subscribe({
    topics: [
      "heartbeats",
      "productionPlan",
      "storageAlerts",
      "batches",
      "storageLevels",
    ],
    fromBeginning: false,
  });

  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      try {
        const parsedMessage = JSON.parse(message.value.toString());
        handleEvent(topic, parsedMessage);
      } catch (error) {
        console.error("Error parsing message:", error);
        // If not JSON, treat as plain text
        handleEvent(topic, { text: message.value.toString() });
      }
    },
  });

  console.log("Connected to Kafka and subscribed to topics");
}

// WebSocket connection handling
wss.on("connection", (ws) => {
  console.log("New client connected");
  clients.add(ws);

  // Send recent events to new client
  Object.entries(recentEvents).forEach(([topic, events]) => {
    events.forEach((event) => {
      ws.send(JSON.stringify(event));
    });
  });

  ws.on("close", () => {
    console.log("Client disconnected");
    clients.delete(ws);
  });

  ws.on("error", (error) => {
    console.error("WebSocket error:", error);
    clients.delete(ws);
  });
});

// REST API endpoints
app.get("/api/events/:topic", (req, res) => {
  const topic = req.params.topic;
  res.json(recentEvents[topic] || []);
});

app.get("/api/events", (req, res) => {
  res.json(recentEvents);
});

app.get("/api/stats", (req, res) => {
  const stats = {};
  Object.entries(recentEvents).forEach(([topic, events]) => {
    stats[topic] = {
      count: events.length,
      latest: events[events.length - 1]?.timestamp,
    };
  });
  res.json(stats);
});

// Start server
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  setupKafka().catch(console.error);
});

// Graceful shutdown
process.on("SIGINT", async () => {
  console.log("Shutting down...");
  await consumer.disconnect();
  server.close();
  process.exit(0);
});
