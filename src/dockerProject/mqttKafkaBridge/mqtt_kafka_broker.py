import logging
import json
import threading
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import paho.mqtt.client as mqtt

# Logger setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s'
)
LOGGER = logging.getLogger(__name__)

# Allowed message titles for filtering
ALLOWED_KAFKA_TO_MQTT = {"AssignBlade", "SwapBlade", "KillMachine"}
ALLOWED_MQTT_TO_KAFKA = {"BladeSwapped", "heartbeat"}


class MqttKafkaBridge:
    """Bridges MQTT and Kafka messages bidirectionally."""

    def __init__(self, mqtt_broker, mqtt_port, kafka_bootstrap_servers):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.mqtt_client = None
        self.kafka_producer = None
        self.kafka_consumer = None

        # Topic mappings
        self.mqtt_to_kafka_topics = {
            'heartbeats': 'heartbeats',
            'productionPlan': 'productionPlan',
            'productionPlan/bladeSwapped': 'productionPlan'  # Added for BladeSwapped
        }

        self.kafka_to_mqtt_topics = {
            'productionPlan': 'productionPlan',
            'updateManager': 'updateManager',
        }

        LOGGER.info("MqttKafkaBridge initialized with MQTT broker: %s:%d, Kafka: %s",
                    mqtt_broker, mqtt_port, kafka_bootstrap_servers)

    def start(self):
        LOGGER.info("Starting MQTT-Kafka Bridge")
        self._init_mqtt_client()
        time.sleep(3)
        for mqtt_topic in self.mqtt_to_kafka_topics.keys():
            self.mqtt_client.subscribe(mqtt_topic, qos=1)
        self._init_kafka_producer()
        kafka_consumer_thread = threading.Thread(target=self._start_kafka_consumer, daemon=True)
        kafka_consumer_thread.start()
        self.mqtt_client.loop_forever()

    def _init_mqtt_client(self):
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)

    def _init_kafka_producer(self):
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8') if isinstance(v, dict)
            else v.encode('utf-8') if isinstance(v, str) else v
        )

    def _on_mqtt_connect(self, client, userdata, connect_flags, reason_code, properties):
        for mqtt_topic in self.mqtt_to_kafka_topics.keys():
            client.subscribe(mqtt_topic)

    def _on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        LOGGER.info("MQTT disconnected")

    def _on_mqtt_message(self, client, userdata, msg):
        mqtt_topic = msg.topic
        payload = msg.payload.decode('utf-8')
        try:
            message_obj = json.loads(payload)
            title = message_obj.get("title", "")
            if title in ALLOWED_MQTT_TO_KAFKA:
                kafka_topic = self.mqtt_to_kafka_topics.get(mqtt_topic)
                if kafka_topic:
                    LOGGER.info("MQTT → Kafka forwarding allowed: title=%s", title)
                    self._forward_mqtt_to_kafka(kafka_topic, payload)
                else:
                    LOGGER.debug("MQTT topic %s not mapped for Kafka", mqtt_topic)
            else:
                LOGGER.debug("MQTT → Kafka message ignored: title=%s", title)
        except Exception as e:
            LOGGER.error("Error processing MQTT message: %s", str(e))

    def _forward_mqtt_to_kafka(self, kafka_topic, payload):
        try:
            try:
                message = json.loads(payload)
            except json.JSONDecodeError:
                message = payload
            self.kafka_producer.send(kafka_topic, value=message)
            self.kafka_producer.flush(timeout=10)
        except Exception as e:
            LOGGER.error("Error forwarding MQTT → Kafka: %s", str(e))

    def _start_kafka_consumer(self):
        topics = list(self.kafka_to_mqtt_topics.keys())
        self.kafka_consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=self.kafka_bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='mqtt-kafka-bridge-v2',
            value_deserializer=lambda m: m.decode('utf-8') if m else None,
        )
        for record in self.kafka_consumer:
            kafka_topic = record.topic
            payload = record.value
            self._forward_kafka_to_mqtt(self.kafka_to_mqtt_topics[kafka_topic], payload)

    def _forward_kafka_to_mqtt(self, mqtt_topic, payload):
        try:
            message_obj = json.loads(payload)
            title = message_obj.get("title", "")
            if title in ALLOWED_KAFKA_TO_MQTT:
                specific_topic = mqtt_topic
                if mqtt_topic == 'productionPlan':
                    if title == "AssignBlade":
                        specific_topic = "productionPlan/assignBlade"
                    elif title == "SwapBlade":
                        specific_topic = "productionPlan/swapBlade"
                elif mqtt_topic == 'updateManager' and title == "KillMachine":
                    specific_topic = "updateManager/killMachine"
                self.mqtt_client.publish(specific_topic, payload=payload, qos=1, retain=False)
                LOGGER.info("Kafka → MQTT published: %s", specific_topic)
            else:
                LOGGER.debug("Kafka → MQTT message ignored: title=%s", title)
        except Exception as e:
            LOGGER.error("Error forwarding Kafka → MQTT: %s", str(e))


def main():
    import os
    mqtt_broker = os.getenv('MQTT_BROKER', 'mosquitto')
    mqtt_port = int(os.getenv('MQTT_PORT', 1883))
    kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    bridge = MqttKafkaBridge(mqtt_broker, mqtt_port, kafka_bootstrap_servers)
    bridge.start()


if __name__ == '__main__':
    main()