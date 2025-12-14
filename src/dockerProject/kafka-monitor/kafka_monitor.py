import json
import logging
import time
from kafka import KafkaConsumer
from datetime import datetime
import threading

# Suppress kafka-python debug logs
logging.getLogger('kafka').setLevel(logging.WARNING)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)
logging.getLogger('kafka.client').setLevel(logging.WARNING)

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
LOGGER = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    RED = '\033[91m'

def format_message(topic, message_json):
    """Format Kafka message for display."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Color based on topic
    if topic == 'heartbeats':
        color = Colors.MAGENTA
        icon = '💓'
    elif topic == 'productionPlan':
        color = Colors.BLUE
        icon = '📋'
    elif topic == 'storageAlerts':
        color = Colors.GREEN
        icon = '📦'
    elif topic == 'experiment':
        color = Colors.YELLOW
        icon = '📦'
    else:
        color = Colors.CYAN
        icon = '🔨'
    
    # Format the message content
    message_str = json.dumps(message_json, indent=2)
    
    # Create formatted output
    header = f"{color}{Colors.BOLD}[{timestamp}] {icon} {topic.upper()}{Colors.RESET}"
    
    print(f"\n{header}")
    print(f"{color}{message_str}{Colors.RESET}")
    print("-" * 80)

def consume_topic(topic_name):
    """Consume messages from a Kafka topic."""
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Create a unique consumer group per topic to read from beginning
            consumer = KafkaConsumer(
                topic_name,
                bootstrap_servers='kafka:29092',
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                group_id=f'kafka-monitor-{topic_name}'  # Unique group per topic
            )
            
            LOGGER.info(f"Consumer for topic '{topic_name}' started - reading from beginning...")
            retry_count = 0  # Reset on successful connection
            
            # Poll indefinitely for messages
            for message in consumer:
                if message.value:
                    try:
                        format_message(topic_name, message.value)
                    except Exception as e:
                        LOGGER.error(f"Error formatting message from {topic_name}: {e}")
        
        except Exception as e:
            retry_count += 1
            LOGGER.warning(f"Error consuming from topic {topic_name} (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(2)  # Wait 2 seconds before retrying
            else:
                LOGGER.error(f"Failed to connect to topic {topic_name} after {max_retries} attempts")
                break


def main():
    """Main monitor function."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 80)
    print("  KAFKA MESSAGE MONITOR - PASTA PRODUCTION SYSTEM")
    print("=" * 80)
    print(f"{Colors.RESET}")
    print(f"Monitoring topics: {Colors.BOLD}heartbeats, productionPlan{Colors.RESET}\n")
    
    topics = ['heartbeats', 'productionPlan', 'storageAlerts', 'experiment']
    
    # Create a thread for each topic
    threads = []
    for topic in topics:
        thread = threading.Thread(
            target=consume_topic,
            args=(topic,),
            daemon=True,
            name=f'ConsumerThread-{topic}'
        )
        thread.start()
        threads.append(thread)
        LOGGER.info(f"Started consumer thread for topic: {topic}")

    # Keep main thread alive
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}\nShutting down monitor...{Colors.RESET}\n")
        LOGGER.info("Monitor stopped by user")

if __name__ == '__main__':
    main()