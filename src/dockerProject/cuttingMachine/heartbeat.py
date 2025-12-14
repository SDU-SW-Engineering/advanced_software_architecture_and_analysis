"""
Heartbeat generation and management with event tracking timestamps
File: cuttingMachine/heartbeat.py
"""

import logging
import json
import time
import threading
from typing import Callable, Optional
from state import MachineState, OperationalState

LOGGER = logging.getLogger(__name__)


class HeartbeatManager:
    """Manages heartbeat generation and sending with timestamp tracking"""

    HEARTBEAT_INTERVAL = 5  # Send heartbeat every 5 seconds

    def __init__(self, machine_id: int, state: MachineState):
        """
        Initialize heartbeat manager.

        Args:
            machine_id (int): Unique machine identifier
            state (MachineState): Reference to machine state
        """
        self.machine_id = machine_id
        self.state = state
        self.publish_callback: Optional[Callable] = None
        self._running = False

    def set_publish_callback(self, callback: Callable) -> None:
        """
        Set callback for publishing heartbeats.

        Args:
            callback (Callable): Function to publish messages
        """
        self.publish_callback = callback

    def start(self) -> None:
        """Start heartbeat cycle in a separate thread"""
        if self._running:
            LOGGER.warning("Heartbeat manager already running")
            return

        self._running = True
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_cycle,
            daemon=True,
            name=f"HeartbeatWorker-{self.machine_id}"
        )
        heartbeat_thread.start()
        LOGGER.info(f"Heartbeat manager started for machine {self.machine_id}")

    def stop(self) -> None:
        """Stop heartbeat cycle"""
        self._running = False
        LOGGER.info(f"Heartbeat manager stopped for machine {self.machine_id}")

    def _heartbeat_cycle(self) -> None:
        """Send heartbeats periodically"""
        while self._running:
            try:
                time.sleep(self.HEARTBEAT_INTERVAL)
                self._send_heartbeat()
            except Exception as e:
                LOGGER.error(f"Error in heartbeat cycle: {str(e)}")

    def _send_heartbeat(self) -> None:
        """Send a heartbeat message with timestamps for event tracking"""
        # Check if in recovery mode
        if self.state.is_in_recovery():
            LOGGER.debug(f"Machine {self.machine_id} in recovery mode, skipping heartbeat")
            return

        # NEW: Capture timestamp at heartbeat generation
        heartbeat_ts = int(time.time() * 1000)  # milliseconds

        # Build heartbeat message based on current state
        try:
            if self.state.is_working():
                # WORKING state with blade type
                blade_type = self.state.get_blade_type()
                message = json.dumps({
                    "title": "heartbeat",
                    "machineId": self.machine_id,
                    "bladeType": blade_type,
                    "timestamp": heartbeat_ts,  # NEW: Add generation timestamp
                    "state": "WORKING"  # NEW: Add state for debugging
                })
                LOGGER.debug(f"Sending heartbeat WITH blade for machine {self.machine_id}, ts={heartbeat_ts}")
                
                # NEW: Log this as a potential "solved_ts" event for newMachine or machineFailure
                self._log_heartbeat_event("heartbeat_with_blade", blade_type, heartbeat_ts)

            elif self.state.is_waiting_for_assignment():
                # WAITING_FOR_ASSIGNMENT state without blade type
                message = json.dumps({
                    "title": "heartbeat",
                    "machineId": self.machine_id,
                    "timestamp": heartbeat_ts,  # NEW: Add generation timestamp
                    "state": "WAITING_FOR_ASSIGNMENT"  # NEW: Add state for debugging
                })
                LOGGER.debug(f"Sending heartbeat WITHOUT blade for machine {self.machine_id}, ts={heartbeat_ts}")
                
                # NEW: Log this as a potential "trigger_ts" event for newMachine
                self._log_heartbeat_event("heartbeat_without_blade", None, heartbeat_ts)

            else:
                # INITIALIZING or other state
                current_state = self.state.get_state()
                LOGGER.debug(f"Machine {self.machine_id} in {current_state.value} state, skipping heartbeat")
                return

            # Publish heartbeat
            if self.publish_callback:
                self.publish_callback("heartbeats", message)
            else:
                LOGGER.warning("Publish callback not set, cannot send heartbeat")

        except Exception as e:
            LOGGER.error(f"Failed to send heartbeat: {str(e)}")

    # NEW: Internal method to log heartbeat events for experiment tracking
    def _log_heartbeat_event(self, event_type: str, blade_type: Optional[str], timestamp: int) -> None:
        """
        Log heartbeat event for event processor correlation.
        
        These logs help the EventProcessor identify when events are solved:
        - heartbeat_without_blade: potential trigger for newMachine event
        - heartbeat_with_blade: potential solved_ts for newMachine or machineFailure
        
        Args:
            event_type: Type of heartbeat (heartbeat_with_blade or heartbeat_without_blade)
            blade_type: Blade type if present (A or B)
            timestamp: Generation timestamp in milliseconds
        """
        event_log = {
            "event_source": "heartbeat",
            "event_type": event_type,
            "machine_id": self.machine_id,
            "blade_type": blade_type,
            "timestamp": timestamp
        }
        
        # Log as special marker so EventProcessor can extract these
        LOGGER.info(f"HEARTBEAT_EVENT: {json.dumps(event_log)}")