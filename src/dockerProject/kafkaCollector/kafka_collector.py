"""
Kafka Event Collector
Collects all Kafka messages during experiments for event correlation
"""

import json
import logging
import time
from kafka import KafkaConsumer
from datetime import datetime
import threading
from pathlib import Path
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
LOGGER = logging.getLogger(__name__)


class KafkaCollector:
    """Collects all Kafka messages and machine logs for event correlation"""

    def __init__(self, bootstrap_servers, output_dir='/app/collector_output'):
        self.bootstrap_servers = bootstrap_servers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSONL files for each topic
        self.files = {}
        self.consumers = {}
        self.threads = {}
        self.running = False
        self.message_counts = {}

        LOGGER.info(f"KafkaCollector initialized with output dir: {self.output_dir}")

    def start(self):
        """Start collecting from all topics"""
        self.running = True
        topics = ['heartbeats', 'productionPlan', 'storageAlerts', 'storageLevels']
        
        for topic in topics:
            # Open file for writing
            file_path = self.output_dir / f'{topic}.jsonl'
            self.files[topic] = open(file_path, 'w')
            self.message_counts[topic] = 0
            
            # Start consumer thread for each topic
            thread = threading.Thread(
                target=self._consume_topic,
                args=(topic,),
                daemon=True,
                name=f'Collector-{topic}'
            )
            thread.start()
            self.threads[topic] = thread
        
        LOGGER.info("KafkaCollector started for topics: heartbeats, productionPlan, storageAlerts, storageLevels")

    def _consume_topic(self, topic):
        """Consume from a single topic"""
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            try:
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=self.bootstrap_servers,
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    group_id=f'collector-{topic}',
                    session_timeout_ms=30000
                )
                
                LOGGER.info(f"Collector subscribed to {topic}")
                retry_count = 0
                
                for message in consumer:
                    if not self.running:
                        break
                    
                    if message.value:
                        try:
                            # Add metadata
                            record = {
                                'topic': topic,
                                'offset': message.offset,
                                'partition': message.partition,
                                'collected_at': int(time.time() * 1000),
                                'message': message.value
                            }
                            
                            # Write to JSONL (one JSON per line)
                            self.files[topic].write(json.dumps(record) + '\n')
                            self.files[topic].flush()
                            self.message_counts[topic] += 1
                            
                        except Exception as e:
                            LOGGER.error(f"Error processing message from {topic}: {e}")
            
            except Exception as e:
                retry_count += 1
                LOGGER.warning(f"Error consuming {topic} (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    LOGGER.error(f"Failed to connect to {topic} after {max_retries} attempts")
                    break

    def stop(self):
        """Stop collecting and close files"""
        self.running = False
        
        # Close all files
        for topic, f in self.files.items():
            f.close()
        
        # Wait for threads to finish
        for topic, thread in self.threads.items():
            thread.join(timeout=5)
        
        # Log summary
        LOGGER.info("KafkaCollector stopped. Message counts:")
        for topic, count in self.message_counts.items():
            LOGGER.info(f"  {topic}: {count} messages")

    def get_message_count(self, topic):
        """Get current message count for a topic"""
        return self.message_counts.get(topic, 0)


def main():
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    output_dir = os.getenv('COLLECTOR_OUTPUT_DIR', '/app/collector_output')
    
    collector = KafkaCollector(bootstrap_servers, output_dir)
    collector.start()
    
    try:
        while True:
            time.sleep(10)
            # Periodically log status
            heartbeat_count = collector.get_message_count('heartbeats')
            production_count = collector.get_message_count('productionPlan')
            alert_count = collector.get_message_count('storageAlerts')
            LOGGER.debug(f"Status - Heartbeats: {heartbeat_count}, ProductionPlan: {production_count}, Alerts: {alert_count}")
    except KeyboardInterrupt:
        LOGGER.info("Shutdown signal received")
        collector.stop()
        LOGGER.info("KafkaCollector shutdown complete")


if __name__ == '__main__':
    main()