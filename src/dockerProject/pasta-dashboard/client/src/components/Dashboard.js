import React from "react";
import "./Dashboard.css";
import EventCard from "./EventCard";
import MachineStatus from "./MachineStatus";
import ProductionStats from "./ProductionStats";

const Dashboard = ({ events, connectionStatus }) => {
  // Extract machine status from heartbeats
  const machines = {};
  events.heartbeats?.forEach((event) => {
    const machineId = event.data.machineId;
    if (machineId !== undefined) {
      machines[machineId] = {
        id: machineId,
        bladeType: event.data.bladeType || "Not Assigned",
        lastSeen: event.timestamp,
        status: "active",
      };
    }
  });

  // Get recent events (last 20 of each type)
  const recentHeartbeats = events.heartbeats?.slice(-20) || [];
  const recentProductionPlan = events.productionPlan?.slice(-20) || [];
  const recentStorageAlerts = events.storageAlerts?.slice(-20) || [];
  const recentBatches = events.batches?.slice(-20) || [];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>🍝 Pasta Production Dashboard</h1>
        <div className={`connection-status ${connectionStatus}`}>
          <span className="status-dot"></span>
          {connectionStatus.toUpperCase()}
        </div>
      </header>

      <div className="dashboard-grid">
        {/* Machine Status */}
        <div className="dashboard-section">
          <h2>Machine Status</h2>
          <div className="machines-grid">
            {Object.values(machines).map((machine) => (
              <MachineStatus key={machine.id} machine={machine} />
            ))}
            {Object.keys(machines).length === 0 && (
              <div className="no-data">No machines detected</div>
            )}
          </div>
        </div>

        {/* Production Statistics */}
        <div className="dashboard-section">
          <h2>Production Statistics</h2>
          <ProductionStats events={events} />
        </div>

        {/* Production Plan Summary */}
        <div className="dashboard-section">
          <h2>📋 Recent Production Plan Actions</h2>
          <div className="production-plan-summary">
            {recentProductionPlan
              .slice(-5)
              .reverse()
              .map((event, index) => (
                <div key={index} className="plan-action-card">
                  <span className="plan-timestamp">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="plan-action">{event.data.title}</span>
                  <div className="plan-details">
                    {event.data.machineId !== undefined && (
                      <span>Machine: {event.data.machineId}</span>
                    )}
                    {event.data.bladeType && (
                      <span>Blade: {event.data.bladeType}</span>
                    )}
                    {event.data.freshAmount !== undefined && (
                      <span>Fresh Amount: {event.data.freshAmount}</span>
                    )}
                  </div>
                </div>
              ))}
            {recentProductionPlan.length === 0 && (
              <div className="no-data">No production plan events yet</div>
            )}
          </div>
        </div>

        {/* Live Events */}
        <div className="dashboard-section events-section">
          <h2>Live Events</h2>

          <div className="events-container">
            {/* Heartbeats */}
            <div className="event-column">
              <h3>💓 Heartbeats</h3>
              <div className="event-list">
                {recentHeartbeats.map((event, index) => (
                  <EventCard key={index} event={event} type="heartbeat" />
                ))}
                {recentHeartbeats.length === 0 && (
                  <div className="no-events">No heartbeats yet</div>
                )}
              </div>
            </div>

            {/* Production Plan */}
            <div className="event-column">
              <h3>📋 Production Plan</h3>
              <div className="event-list">
                {recentProductionPlan.map((event, index) => (
                  <EventCard key={index} event={event} type="production" />
                ))}
                {recentProductionPlan.length === 0 && (
                  <div className="no-events">No production events yet</div>
                )}
              </div>
            </div>

            {/* Storage Alerts */}
            <div className="event-column">
              <h3>⚠️ Storage Alerts</h3>
              <div className="event-list">
                {recentStorageAlerts.map((event, index) => (
                  <EventCard key={index} event={event} type="alert" />
                ))}
                {recentStorageAlerts.length === 0 && (
                  <div className="no-events">No storage alerts</div>
                )}
              </div>
            </div>

            {/* Batches */}
            <div className="event-column">
              <h3>📦 New Batches</h3>
              <div className="event-list">
                {recentBatches.map((event, index) => (
                  <EventCard key={index} event={event} type="batch" />
                ))}
                {recentBatches.length === 0 && (
                  <div className="no-events">No new batches yet</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
