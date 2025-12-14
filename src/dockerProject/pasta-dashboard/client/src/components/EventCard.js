import React from "react";

const EventCard = ({ event, type }) => {
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getEventColor = (type) => {
    switch (type) {
      case "heartbeat":
        return "#3b82f6"; // blue
      case "production":
        return "#8b5cf6"; // purple
      case "alert":
        return "#ef4444"; // red
      case "batch":
        return "#10b981"; // green
      default:
        return "#6b7280"; // gray
    }
  };

  const renderEventData = () => {
    const data = event.data;

    if (type === "heartbeat") {
      return (
        <div className="event-data">
          <span>Machine {data.machineId}</span>
          {data.bladeType && (
            <span className="blade-type">Blade: {data.bladeType}</span>
          )}
        </div>
      );
    }

    if (type === "production") {
      return (
        <div className="event-data">
          <span className="event-title">{data.title}</span>
          {data.machineId !== undefined && (
            <span>Machine: {data.machineId}</span>
          )}
          {data.bladeType && (
            <span className="blade-type">Blade: {data.bladeType}</span>
          )}
          {data.freshAmount !== undefined && (
            <span className="fresh-amount">
              Fresh Amount: {data.freshAmount}
            </span>
          )}

          {/* Enhanced display based on production plan event types */}
          {data.title === "AssignBlade" && (
            <span className="action-description">
              🔧 Assigning blade to new machine
            </span>
          )}
          {data.title === "SwapBlade" && (
            <span className="action-description">
              🔄 Swapping blade due to failure
            </span>
          )}
          {data.title === "ChangeFreshAmount" && (
            <span className="action-description">
              📊 Adjusting production ratio
            </span>
          )}
          {data.title === "BladeSwapped" && (
            <span className="action-description">✅ Blade swap completed</span>
          )}
          {data.title === "FreshAmountChanged" && (
            <span className="action-description">
              ✅ Production ratio updated
            </span>
          )}
        </div>
      );
    }

    if (type === "alert") {
      return (
        <div className="event-data">
          <span className="event-title">{data.title}</span>
          {data.aFresh && <span>A-Fresh: {data.aFresh}%</span>}
          {data.aDry && <span>A-Dry: {data.aDry}%</span>}
          {data.bFresh && <span>B-Fresh: {data.bFresh}%</span>}
          {data.bDry && <span>B-Dry: {data.bDry}%</span>}
        </div>
      );
    }

    if (type === "batch") {
      return (
        <div className="event-data">
          <span className="event-title">{data.title}</span>
          {data.bladeType && <span>Type: {data.bladeType}</span>}
          {data.freshness && <span>Freshness: {data.freshness}</span>}
        </div>
      );
    }

    // Default rendering for unknown types
    return (
      <div className="event-data">
        <pre>{JSON.stringify(data, null, 2)}</pre>
      </div>
    );
  };

  return (
    <div
      className="event-card"
      style={{ borderLeft: `4px solid ${getEventColor(type)}` }}
    >
      <div className="event-header">
        <span className="event-time">{formatTime(event.timestamp)}</span>
      </div>
      {renderEventData()}
    </div>
  );
};

export default EventCard;
