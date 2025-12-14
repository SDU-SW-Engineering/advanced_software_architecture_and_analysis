import React from "react";

const MachineStatus = ({ machine }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case "active":
        return "#10b981"; // green
      case "warning":
        return "#f59e0b"; // yellow
      case "error":
        return "#ef4444"; // red
      default:
        return "#6b7280"; // gray
    }
  };

  const timeSinceLastSeen = (timestamp) => {
    const now = new Date();
    const lastSeen = new Date(timestamp);
    const diffMs = now - lastSeen;
    const diffSeconds = Math.floor(diffMs / 1000);

    if (diffSeconds < 60) {
      return `${diffSeconds}s ago`;
    } else {
      const diffMinutes = Math.floor(diffSeconds / 60);
      return `${diffMinutes}m ago`;
    }
  };

  return (
    <div className="machine-card">
      <div className="machine-header">
        <h4>Machine {machine.id}</h4>
        <div
          className="status-indicator"
          style={{ backgroundColor: getStatusColor(machine.status) }}
        />
      </div>
      <div className="machine-details">
        <div className="machine-field">
          <span className="field-label">Blade Type:</span>
          <span className="field-value">{machine.bladeType}</span>
        </div>
        <div className="machine-field">
          <span className="field-label">Last Seen:</span>
          <span className="field-value">
            {timeSinceLastSeen(machine.lastSeen)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default MachineStatus;
