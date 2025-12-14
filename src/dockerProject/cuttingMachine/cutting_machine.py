"""
Cutting Machine core orchestrator
Coordinates MQTT, state, heartbeats, and message handling
"""

import logging
import time
from state import MachineState, OperationalState
from mqtt_manager import MqttManager
from message_handler import MessageHandler
from heartbeat import HeartbeatManager

LOGGER = logging.getLogger(__name__)


class CuttingMachine:
    """Represents a cutting machine in the production system"""

    def __init__(self, machine_id: int, mqtt_broker: str, mqtt_port: int):
        """
        Initialize cutting machine.

        Args:
            machine_id (int): Unique identifier for this machine
            mqtt_broker (str): MQTT broker hostname/IP
            mqtt_port (int): MQTT broker port
        """
        self.machine_id = machine_id
        LOGGER.info(f"Initializing CuttingMachine {self.machine_id}")

        # Core components
        self.state = MachineState()
        self.mqtt = MqttManager(mqtt_broker, mqtt_port, machine_id)
        self.message_handler = MessageHandler(machine_id, self.state)
        self.heartbeat = HeartbeatManager(machine_id, self.state)

        # Wire up callbacks
        self.mqtt.set_message_callback(self.message_handler.process_message)
        self.message_handler.set_publish_callback(self.mqtt.publish)
        self.heartbeat.set_publish_callback(self.mqtt.publish)

        LOGGER.info(f"CuttingMachine {self.machine_id} initialized successfully")

    def start(self) -> None:
        """Start the cutting machine"""
        LOGGER.info(f"Starting Cutting Machine {self.machine_id}")

        # Connect to MQTT
        self.mqtt.connect()

        # Wait for subscriptions to stabilize
        time.sleep(2)

        # Transition to WAITING_FOR_ASSIGNMENT state
        self.state.set_state(OperationalState.WAITING_FOR_ASSIGNMENT)
        LOGGER.info(f"Machine {self.machine_id} ready and waiting for blade assignment")

        # Start heartbeat cycle
        self.heartbeat.start()

        LOGGER.info(f"✅ Cutting Machine {self.machine_id} started successfully")

    def stop(self) -> None:
        """Stop the cutting machine"""
        LOGGER.info(f"Stopping Cutting Machine {self.machine_id}")

        self.heartbeat.stop()
        self.mqtt.disconnect()

        LOGGER.info(f"Cutting Machine {self.machine_id} stopped")