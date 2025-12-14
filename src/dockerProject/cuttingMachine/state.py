"""
CuttingMachine state management with event logging for experiment tracking
File: cuttingMachine/state.py
"""

from enum import Enum
import threading
from typing import Optional
import time
import json
import logging

LOGGER = logging.getLogger(__name__)


class OperationalState(Enum):
    """Machine operational states"""
    INITIALIZING = "INITIALIZING"
    WAITING_FOR_ASSIGNMENT = "WAITING_FOR_ASSIGNMENT"
    WORKING = "WORKING"
    RECOVERY = "RECOVERY"


class MachineState:
    """Manages the operational state of a cutting machine with event tracking"""

    def __init__(self):
        """Initialize machine state"""
        self._state = OperationalState.INITIALIZING
        self._blade_type: Optional[str] = None
        self._recovery_end_time: float = 0
        self._lock = threading.Lock()

    def get_state(self) -> OperationalState:
        """Get current operational state"""
        with self._lock:
            return self._state

    def set_state(self, new_state: OperationalState) -> None:
        """Set operational state"""
        with self._lock:
            old_state = self._state
            self._state = new_state
            
            # NEW: Log state transition event
            self._log_event("state_transition", {
                "old_state": old_state.value,
                "new_state": new_state.value
            })

    def get_blade_type(self) -> Optional[str]:
        """Get current blade type"""
        with self._lock:
            return self._blade_type

    def set_blade_type(self, blade_type: str) -> None:
        """Set blade type"""
        with self._lock:
            old_blade = self._blade_type
            self._blade_type = blade_type
            
            # NEW: Log blade type change
            self._log_event("blade_type_changed", {
                "old_blade_type": old_blade,
                "new_blade_type": blade_type
            })

    def assign_blade(self, blade_type: str) -> None:
        """Assign blade and transition to WORKING state (triggered by AssignBlade message)"""
        with self._lock:
            old_state = self._state
            old_blade = self._blade_type
            
            self._blade_type = blade_type
            self._state = OperationalState.WORKING
            
            # NEW: Log event with full context and timestamp
            self._log_event("blade_assigned", {
                "blade_type": blade_type,
                "old_state": old_state.value,
                "new_state": OperationalState.WORKING.value,
                "event_type": "newMachine"  # This is the "solved_ts" event for newMachine events
            })

    def swap_blade(self, new_blade_type: str) -> tuple:
        """Swap blade and return old and new types (triggered by SwapBlade message)"""
        with self._lock:
            old_blade_type = self._blade_type
            self._blade_type = new_blade_type
            
            # NEW: Log event with full context and timestamp
            self._log_event("blade_swapped", {
                "old_blade_type": old_blade_type,
                "new_blade_type": new_blade_type,
                "event_type": "machineFailure"  # This is the "solved_ts" event for machineFailure events
            })
            
            return old_blade_type, new_blade_type

    def enter_recovery(self, recovery_seconds: int) -> None:
        """Enter recovery mode for specified seconds (triggered by killMachine message)"""
        with self._lock:
            self._recovery_end_time = time.time() + recovery_seconds
            self._state = OperationalState.RECOVERY
            
            # NEW: Log recovery event
            self._log_event("entered_recovery", {
                "recovery_seconds": recovery_seconds,
                "recovery_end_time": int(self._recovery_end_time * 1000)
            })

    def is_in_recovery(self) -> bool:
        """Check if machine is in recovery mode"""
        with self._lock:
            if self._recovery_end_time > 0:
                current_time = time.time()
                if current_time < self._recovery_end_time:
                    return True
                else:
                    # NEW: Log recovery exit event
                    self._log_event("exited_recovery", {
                        "recovery_end_time": int(self._recovery_end_time * 1000),
                        "exit_time": int(current_time * 1000)
                    })
                    self._recovery_end_time = 0
                    # Transition back to WAITING_FOR_ASSIGNMENT
                    self._state = OperationalState.WAITING_FOR_ASSIGNMENT
                    return False
            return False

    def exit_recovery(self) -> None:
        """Exit recovery mode"""
        with self._lock:
            if self._recovery_end_time > 0:
                self._log_event("manual_recovery_exit", {})
            self._recovery_end_time = 0

    def is_working(self) -> bool:
        """Check if machine is in working state with blade assigned"""
        with self._lock:
            return self._state == OperationalState.WORKING and self._blade_type is not None

    def is_waiting_for_assignment(self) -> bool:
        """Check if machine is waiting for blade assignment"""
        with self._lock:
            return self._state == OperationalState.WAITING_FOR_ASSIGNMENT

    # NEW: Internal method to log state events for experiment tracking
    def _log_event(self, event_type: str, metadata: dict) -> None:
        """
        Log a state event for experiment analysis.
        
        Events are logged as structured JSON to LOGGER for collection by EventProcessor.
        
        Args:
            event_type: Type of event (blade_assigned, blade_swapped, etc.)
            metadata: Additional metadata for the event
        """
        event_log = {
            "event_source": "machine_state",
            "event_type": event_type,
            "timestamp": int(time.time() * 1000),  # milliseconds for consistency
            "state": self._state.value,
            "blade_type": self._blade_type,
            **metadata
        }
        
        # Log as special marker so EventProcessor can extract these
        LOGGER.info(f"STATE_EVENT: {json.dumps(event_log)}")