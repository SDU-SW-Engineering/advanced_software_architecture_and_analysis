import logging
import threading
from database import DatabaseConnection
from kafka_producer import KafkaProducerManager
from batch_manager import BatchManager

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s'
)
LOGGER = logging.getLogger(__name__)


def main():
    """Main entry point for the simulation engine."""
    LOGGER.info("Starting Pasta Production Simulation Engine")
    
    # Initialize connections
    LOGGER.info("Initializing database connection...")
    db = DatabaseConnection(db_url='postgresql://user:password@db:5432/mydatabase')
    
    LOGGER.info("Initializing Kafka producer...")
    kafka = KafkaProducerManager(bootstrap_servers='kafka:29092')
    
    # Initialize managers
    LOGGER.info("Initializing batch manager...")
    batch_manager = BatchManager(db, kafka, kafka_bootstrap_servers='kafka:29092')
    
    # Start batch manager consumers
    LOGGER.info("Starting batch manager consumers...")
    batch_manager.start_production_plan_consumer()
    batch_manager.start_heartbeat_consumer()
    
    LOGGER.info("All worker threads started. Simulation engine running...")
    
    # Keep the main thread alive
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown signal received")
        db.close()
        kafka.close()
        LOGGER.info("Simulation engine stopped")


if __name__ == '__main__':
    main()