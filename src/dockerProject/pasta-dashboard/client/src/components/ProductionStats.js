import React from "react";

const ProductionStats = ({ events }) => {
  // Calculate statistics from events
  const heartbeatCount = events.heartbeats?.length || 0;
  const productionEventCount = events.productionPlan?.length || 0;
  const batchCount = events.batches?.length || 0;
  const alertCount = events.storageAlerts?.length || 0;

  // Get unique machines
  const uniqueMachines = new Set();
  events.heartbeats?.forEach((event) => {
    if (event.data.machineId !== undefined) {
      uniqueMachines.add(event.data.machineId);
    }
  });

  // Calculate events per minute (last 5 minutes)
  const now = new Date();
  const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);

  const recentEvents =
    events.heartbeats?.filter(
      (event) => new Date(event.timestamp) > fiveMinutesAgo
    ).length || 0;

  const eventsPerMinute = Math.round(recentEvents / 5);

  const stats = [
    {
      label: "Active Machines",
      value: uniqueMachines.size,
      color: "#3b82f6",
    },
    {
      label: "Total Heartbeats",
      value: heartbeatCount,
      color: "#10b981",
    },
    {
      label: "Production Events",
      value: productionEventCount,
      color: "#8b5cf6",
    },
    {
      label: "Batches Created",
      value: batchCount,
      color: "#f59e0b",
    },
    {
      label: "Storage Alerts",
      value: alertCount,
      color: "#ef4444",
    },
    {
      label: "Events/min",
      value: eventsPerMinute,
      color: "#6b7280",
    },
  ];

  return (
    <div className="production-stats">
      {stats.map((stat, index) => (
        <div key={index} className="stat-card">
          <div className="stat-value" style={{ color: stat.color }}>
            {stat.value}
          </div>
          <div className="stat-label">{stat.label}</div>
        </div>
      ))}
    </div>
  );
};

export default ProductionStats;
