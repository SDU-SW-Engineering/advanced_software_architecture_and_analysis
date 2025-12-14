import logging
import time
from confluent_kafka import Producer

# Logger setup
LOGGER = logging.getLogger(__name__)


class KafkaProducerManager:
    """Manages Kafka producer with connection retry logic."""
    
    def __init__(self, bootstrap_servers='kafka:29092', max_retries=None):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            max_retries (int): Maximum retry attempts. None = infinite retries
        """
        self.bootstrap_servers = bootstrap_servers
        self.max_retries = max_retries
        self.producer = None
        self._connect()
    
    def _connect(self):
        """Establish Kafka producer connection with retry logic."""
        retries = 0
        while self.producer is None:
            try:
                config = {
                    'bootstrap.servers': self.bootstrap_servers,
                    'client.id': 'pasta-system-producer'
                }
                self.producer = Producer(config)
                LOGGER.info(f"Connected to Kafka at {self.bootstrap_servers}")
                return
            except Exception as e:
                retries += 1
                if self.max_retries and retries >= self.max_retries:
                    LOGGER.error(f"Failed to connect to Kafka after {self.max_retries} attempts: {str(e)}")
                    raise
                LOGGER.warning(f"Kafka connection failed: {str(e)}. Retrying in 5 seconds...")
                time.sleep(5)
    
    def send_message(self, topic, message, key=None):
        """
        Send a message to a Kafka topic.
        
        Args:
            topic (str): Kafka topic name
            message (str): Message to send
            key (str): Optional message key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.producer.produce(
                topic,
                key=key.encode('utf-8') if key else None,
                value=message.encode('utf-8') if isinstance(message, str) else message
            )
            self.producer.flush(30)  # Wait up to 30 seconds for delivery
            return True
        except Exception as e:
            LOGGER.error(f"Failed to send message to topic '{topic}': {str(e)}")
            return False
    
    def send_alert(self, product_type, storage_level):
        """
        Send a production plan alert to Kafka.
        
        Args:
            product_type (str): Product identifier (e.g., "A-fresh", "B-dry")
            storage_level (float): Current storage level percentage
        """
        message = f"Change Production Plan for {product_type} - Level: {storage_level:.2f}%"
        return self.send_message('storageLevels', message, key='Production')
    
    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.flush()
            LOGGER.info("Kafka producer closed")