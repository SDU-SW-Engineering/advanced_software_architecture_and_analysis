"""
MQTT communication management for cutting machines
"""

import logging
import time
from typing import Callable, Optional
import paho.mqtt.client as mqtt

LOGGER = logging.getLogger(__name__)


class MqttManager:
    """Manages MQTT connection and message handling"""

    def __init__(self, broker: str, port: int, machine_id: int):
        """
        Initialize MQTT manager.

        Args:
            broker (str): MQTT broker hostname
            port (int): MQTT broker port
            machine_id (int): Unique machine identifier
        """
        self.broker = broker
        self.port = port
        self.machine_id = machine_id
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.message_callback: Optional[Callable] = None

    def connect(self) -> None:
        """Connect to MQTT broker with retry logic"""
        max_retries = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"cuttingmachine-{self.machine_id}"
                )

                # Set callbacks
                self.client.on_connect = self._on_connect
                self.client.on_message = self._on_message
                self.client.on_disconnect = self._on_disconnect

                LOGGER.info(
                    f"Attempting to connect to MQTT broker {self.broker}:{self.port} "
                    f"(attempt {retry_count + 1}/{max_retries})"
                )
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()  # Start background thread

                # Wait for connection confirmation
                connection_timeout = 10
                start_time = time.time()
                while not self.connected and (time.time() - start_time) < connection_timeout:
                    time.sleep(0.1)

                if self.connected:
                    LOGGER.info(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
                    return
                else:
                    LOGGER.warning("Connection established but not confirmed, retrying...")
                    retry_count += 1
                    time.sleep(2)

            except Exception as e:
                retry_count += 1
                LOGGER.warning(
                    f"Failed to connect to MQTT broker (attempt {retry_count}/{max_retries}): {str(e)}"
                )
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    LOGGER.error(f"Failed to connect to MQTT after {max_retries} attempts")
                    raise RuntimeError("Could not connect to MQTT broker")

    def set_message_callback(self, callback: Callable) -> None:
        """
        Set callback function for message processing.

        Args:
            callback (Callable): Function to handle messages
        """
        self.message_callback = callback

    def subscribe_to_topics(self) -> None:
        """Subscribe to command topics"""
        if not self.client or not self.connected:
            LOGGER.error("Cannot subscribe: MQTT client not connected")
            return

        topics = [
            "productionPlan/assignBlade",
            "productionPlan/swapBlade",
            "updateManager/killMachine"
        ]

        for topic in topics:
            try:
                self.client.subscribe(topic, qos=1)
                LOGGER.info(f"✅ Subscribed to topic: {topic}")
            except Exception as e:
                LOGGER.error(f"❌ Failed to subscribe to {topic}: {str(e)}")

    def publish(self, topic: str, message: str, qos: int = 1) -> None:
        """
        Publish a message to a topic.

        Args:
            topic (str): Target topic
            message (str): Message to publish
            qos (int): Quality of Service level (default: 1)
        """
        if not self.client or not self.connected:
            LOGGER.error(f"Cannot publish to {topic}: MQTT client not connected")
            return

        try:
            self.client.publish(topic, message, qos=qos)
            LOGGER.debug(f"Published to {topic}: {message[:80]}")
        except Exception as e:
            LOGGER.error(f"Failed to publish to {topic}: {str(e)}")

    def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                LOGGER.info("Disconnected from MQTT broker")
            except Exception as e:
                LOGGER.error(f"Error disconnecting from MQTT: {str(e)}")

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        """MQTT connection callback"""
        if reason_code != 0:
            LOGGER.error(f"MQTT connection failed with reason code: {reason_code}")
            self.connected = False
        else:
            LOGGER.info("MQTT client connected successfully")
            self.connected = True
            self.subscribe_to_topics()

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """MQTT disconnection callback"""
        if reason_code != 0:
            LOGGER.warning(f"Unexpected MQTT disconnection with reason code: {reason_code}")
        else:
            LOGGER.info("MQTT client disconnected cleanly")
        self.connected = False

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            LOGGER.info(f"📨 Message arrived on topic {topic}: {payload}")

            # Invoke registered callback if available
            if self.message_callback:
                self.message_callback(topic, payload)

        except Exception as e:
            LOGGER.error(f"Error processing MQTT message: {str(e)}")