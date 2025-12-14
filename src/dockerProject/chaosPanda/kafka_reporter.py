"""
Kafka event reporting for chaos events
"""

import logging
import json
from confluent_kafka import Producer

LOGGER = logging.getLogger(__name__)


class KafkaReporter:
    """Reports chaos events to Kafka"""

    def __init__(self, bootstrap_servers, test_name):
        """
        Initialize Kafka reporter.

        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            test_name (str): Test name for correlation
        """
        self.bootstrap_servers = bootstrap_servers
        self.test_name = test_name

        try:
            config = {
                'bootstrap.servers': bootstrap_servers,
                'client.id': f'chaospanda-{test_name}'
            }
            self.producer = Producer(config)
            LOGGER.info(f"✅ Connected to Kafka at {bootstrap_servers}")
        except Exception as e:
            LOGGER.error(f"Failed to connect to Kafka: {str(e)}")
            raise RuntimeError("Could not connect to Kafka")

    def report_killing_machine(self, machine_id):
        """
        Report killing a cutting machine.

        Args:
            machine_id (int or str): Machine identifier
        """
        try:
            message = {
                "title": "KillingMachine",
                "machineId": machine_id,
                "testName": self.test_name,
                "timestamp": self._get_timestamp()
            }
            
            self._send_to_kafka("experiment", message)
            LOGGER.debug(f"Reported KillingMachine event for machine {machine_id}")

        except Exception as e:
            LOGGER.error(f"Error reporting killing machine: {str(e)}")

    def report_killing_scheduler(self, scheduler_role, scheduler_name):
        """
        Report killing a scheduler.

        Args:
            scheduler_role (str): 'active' or 'shadow'
            scheduler_name (str): Container name or pod name
        """
        try:
            message = {
                "title": "KillingScheduler",
                "schedulerRole": scheduler_role,
                "schedulerName": scheduler_name,
                "testName": self.test_name,
                "timestamp": self._get_timestamp()
            }
            
            self._send_to_kafka("experiment", message)
            LOGGER.debug(f"Reported KillingScheduler event for {scheduler_role} scheduler")

        except Exception as e:
            LOGGER.error(f"Error reporting killing scheduler: {str(e)}")

    def _send_to_kafka(self, topic, message):
        """
        Send message to Kafka topic.

        Args:
            topic (str): Topic name
            message (dict): Message to send
        """
        try:
            json_message = json.dumps(message)
            self.producer.produce(
                topic,
                key=None,
                value=json_message.encode('utf-8')
            )
            self.producer.flush(timeout=10)

        except Exception as e:
            LOGGER.error(f"Error sending to Kafka topic {topic}: {str(e)}")

    @staticmethod
    def _get_timestamp():
        """Get ISO format timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"