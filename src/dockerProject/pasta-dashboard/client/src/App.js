import React, { useState, useEffect } from "react";
import "./App.css";
import Dashboard from "./components/Dashboard";
import useWebSocket from "./hooks/useWebSocket";

function App() {
  const [events, setEvents] = useState({
    heartbeats: [],
    productionPlan: [],
    storageAlerts: [],
    batches: [],
    storageLevels: [],
  });

  const [connectionStatus, setConnectionStatus] = useState("connecting");

  // WebSocket hook
  const { lastMessage, readyState } = useWebSocket("ws://localhost:3001");

  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const event = JSON.parse(lastMessage.data);
        setEvents((prevEvents) => ({
          ...prevEvents,
          [event.topic]: [
            ...(prevEvents[event.topic] || []).slice(-99), // Keep last 100 events
            event,
          ],
        }));
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    const status =
      readyState === 1
        ? "connected"
        : readyState === 0
        ? "connecting"
        : readyState === 2
        ? "closing"
        : "disconnected";
    setConnectionStatus(status);
  }, [readyState]);

  return (
    <div className="App">
      <Dashboard events={events} connectionStatus={connectionStatus} />
    </div>
  );
}

export default App;
