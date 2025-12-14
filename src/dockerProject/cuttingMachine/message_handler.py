"""
Message handling for cutting machine commands with event tracking
File: cuttingMachine/message_handler.py
"""

import logging
import json
import time
from typing import Callable, Optional
from state import MachineState

LOGGER = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming MQTT messages and executes commands with event tracking"""

    def __init__(self, machine_id: int, state: MachineState):
        """
        Initialize message handler.

        Args:
            machine_id (int): Unique machine identifier
            state (MachineState): Reference to machine state
        """
        self.machine_id = machine_id
        self.state = state
        self.publish_callback: Optional[Callable] = None

    def set_publish_callback(self, callback: Callable) -> None:
        """
        Set callback for publishing messages.

        Args:
            callback (Callable): Function to publish messages
        """
        self.publish_callback = callback

    def process_message(self, topic: str, payload: str) -> None:
        """
        Process incoming message with event tracking.

        Args:
            topic (str): MQTT topic
            payload (str): Message payload
        """
        message_ts = int(time.time() * 1000)  # NEW: Capture message receive timestamp
        
        try:
            json_payload = json.loads(payload)
            message_title = json_payload.get("title", "")

            # IMPORTANT: Ignore our own confirmation messages to prevent loops
            if message_title == "BladeSwapped":
                LOGGER.debug(f"Ignoring BladeSwapped confirmation message (our own output)")
                return

            if message_title == "AssignBlade":
                self._handle_assign_blade(json_payload, message_ts)
            elif message_title == "SwapBlade":
                self._handle_swap_blade(json_payload, message_ts)
            elif message_title == "killMachine":
                self._handle_kill_machine(json_payload, message_ts)
            else:
                LOGGER.debug(f"Unknown message title: {message_title}")

        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse JSON from topic {topic}: {str(e)}")
        except Exception as e:
            LOGGER.error(f"Error processing message: {str(e)}")

    def _handle_assign_blade(self, json_payload: dict, message_ts: int) -> None:
        """
        Handle AssignBlade command (trigger for newMachine event).

        Args:
            json_payload (dict): Parsed JSON message
            message_ts (int): Message receive timestamp in milliseconds
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"AssignBlade for different machine {machine_id}, ignoring")
            return

        blade_type = json_payload.get("bladeType")

        if blade_type is None:
            LOGGER.error("AssignBlade message missing bladeType")
            return

        # NEW: Extract event context if present
        event_context = json_payload.get("eventContext", "unknown")
        reaction_ts = json_payload.get("reactionTs", message_ts)

        self.state.assign_blade(blade_type)
        
        # NEW: Log command received with event context
        self._log_command_event("assign_blade_received", {
            "blade_type": blade_type,
            "event_context": event_context,
            "reaction_ts": reaction_ts,
            "message_ts": message_ts
        })
        
        LOGGER.info(
            f"✅ Machine {self.machine_id} ASSIGNED blade type {blade_type} - NOW WORKING "
            f"(eventContext: {event_context})"
        )

    def _handle_swap_blade(self, json_payload: dict, message_ts: int) -> None:
        """
        Handle SwapBlade command (trigger for machineFailure event).

        Args:
            json_payload (dict): Parsed JSON message
            message_ts (int): Message receive timestamp in milliseconds
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"SwapBlade for different machine {machine_id}, ignoring")
            return

        new_blade_type = json_payload.get("bladeType")

        if new_blade_type is None:
            LOGGER.error("SwapBlade message missing bladeType")
            return

        # Check if blade type is already set to the new type (prevents duplicate processing)
        current_blade = self.state.get_blade_type()
        LOGGER.info(f"SwapBlade received: current_blade={current_blade}, new_blade={new_blade_type}")
        
        if current_blade == new_blade_type:
            LOGGER.warning(f"⚠️ Blade already set to {new_blade_type}, blocking duplicate")
            return

        try:
            # NEW: Extract event context if present
            event_context = json_payload.get("eventContext", "unknown")
            reaction_ts = json_payload.get("reactionTs", message_ts)

            LOGGER.info(
                f"Machine {self.machine_id} received blade swap command, sleeping 2 seconds... "
                f"(eventContext: {event_context})"
            )
            
            # Sleep 2 seconds before confirming swap
            time.sleep(2)
            
            old_blade_type, new_blade = self.state.swap_blade(new_blade_type)

            LOGGER.info(
                f"🔄 Machine {self.machine_id} swapped blade from {old_blade_type} to {new_blade_type}"
            )

            # NEW: Log command received with event context
            self._log_command_event("swap_blade_received", {
                "old_blade_type": old_blade_type,
                "new_blade_type": new_blade_type,
                "event_context": event_context,
                "reaction_ts": reaction_ts,
                "message_ts": message_ts
            })

            # Send confirmation
            if self.publish_callback:
                message = json.dumps({
                    "title": "BladeSwapped",
                    "machineId": self.machine_id,
                    "timestamp": int(time.time() * 1000),  # NEW: Add confirmation timestamp
                    "oldBladeType": old_blade_type,  # NEW: Track what was swapped
                    "newBladeType": new_blade_type  # NEW: Track what was swapped to
                })
                LOGGER.info(f"📤 Publishing BladeSwapped message...")
                self.publish_callback("productionPlan/bladeSwapped", message)
                LOGGER.info(f"✅ Machine {self.machine_id} sent BladeSwapped confirmation")
            else:
                LOGGER.error("Publish callback not set!")

        except Exception as e:
            LOGGER.error(f"Error handling blade swap: {str(e)}", exc_info=True)

    def _handle_kill_machine(self, json_payload: dict, message_ts: int) -> None:
        """
        Handle killMachine command (triggers machine failure recovery).

        Args:
            json_payload (dict): Parsed JSON message
            message_ts (int): Message receive timestamp in milliseconds
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"KillMachine for different machine {machine_id}, ignoring")
            return

        recovery_time = json_payload.get("recoveryTime", 0)

        if recovery_time <= 0:
            LOGGER.error(f"KillMachine message invalid recoveryTime: {recovery_time}")
            return

        self.state.enter_recovery(recovery_time)
        
        # NEW: Log command received
        self._log_command_event("kill_machine_received", {
            "recovery_time": recovery_time,
            "message_ts": message_ts
        })
        
        LOGGER.warning(
            f"Machine {self.machine_id} entering recovery mode for {recovery_time} seconds"
        )

    # NEW: Internal method to log command events for experiment tracking
    def _log_command_event(self, event_type: str, metadata: dict) -> None:
        """
        Log command event for event processor correlation.
        
        These logs help the EventProcessor track which commands the machine received
        and when they were processed.
        
        Args:
            event_type: Type of command (assign_blade_received, swap_blade_received, etc.)
            metadata: Additional metadata about the command
        """
        event_log = {
            "event_source": "message_handler",
            "event_type": event_type,
            "machine_id": self.machine_id,
            "timestamp": int(time.time() * 1000),  # milliseconds
            **metadata
        }
        
        # Log as special marker so EventProcessor can extract these
        LOGGER.info(f"COMMAND_EVENT: {json.dumps(event_log)}")