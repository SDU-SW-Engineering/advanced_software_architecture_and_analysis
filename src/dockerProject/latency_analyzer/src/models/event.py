"""Event data models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Event:
    """Base event class representing a latency event."""
    
    id: str
    type: str
    trigger_ts: int
    reaction_ts: int
    solved_ts: int
    scheduler_latency: int
    machine_latency: int
    
    @property
    def total_latency(self) -> int:
        """Calculate total latency."""
        return self.scheduler_latency + self.machine_latency
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for CSV export."""
        return {
            'id': self.id,
            'type': self.type,
            'trigger_ts': self.trigger_ts,
            'reaction_ts': self.reaction_ts,
            'solved_ts': self.solved_ts,
            'scheduler_latency': self.scheduler_latency,
            'machine_latency': self.machine_latency
        }
    
    def __repr__(self) -> str:
        return (f"Event(id={self.id}, type={self.type}, "
                f"scheduler_latency={self.scheduler_latency}, "
                f"machine_latency={self.machine_latency})")