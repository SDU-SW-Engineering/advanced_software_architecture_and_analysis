#!/usr/bin/env python3
"""
Main entry point for Cutting Machine Simulator
"""

import logging
import os
import time
from cutting_machine import CuttingMachine

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s'
)
LOGGER = logging.getLogger(__name__)


def main():
    """Main entry point"""
    # Get environment variables
    machine_id_str = os.getenv("MACHINE_ID")
    mqtt_broker = os.getenv("MQTT_BROKER", "mosquitto")
    mqtt_port_str = os.getenv("MQTT_PORT", "1883")

    # Validate inputs
    if not machine_id_str:
        LOGGER.error("MACHINE_ID environment variable not set")
        exit(1)

    try:
        machine_id = int(machine_id_str)
        mqtt_port = int(mqtt_port_str)
    except ValueError as e:
        LOGGER.error(f"Invalid environment variables: {str(e)}")
        exit(1)

    # Create and start machine
    try:
        machine = CuttingMachine(machine_id, mqtt_broker, mqtt_port)
        machine.start()

        LOGGER.info(f"Cutting Machine {machine_id} started successfully")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        LOGGER.info("Shutdown signal received")
        machine.stop()
    except Exception as e:
        LOGGER.error(f"Fatal error: {str(e)}")
        exit(1)


if __name__ == '__main__':
    main()