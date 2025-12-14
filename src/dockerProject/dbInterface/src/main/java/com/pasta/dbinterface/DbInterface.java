package com.pasta.dbinterface;

import com.pasta.dbinterface.db.DatabaseManager;
import com.pasta.dbinterface.kafka.KafkaProducerManager;
import com.pasta.dbinterface.storage.StorageMonitor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DbInterface {
    private static final Logger LOGGER = LoggerFactory.getLogger(DbInterface.class);

    private final DatabaseManager databaseManager;
    private final KafkaProducerManager kafkaProducer;
    private final StorageMonitor storageMonitor;

    public DbInterface(String dbUrl, String kafkaBootstrapServers) {
        this.databaseManager = new DatabaseManager(dbUrl);
        this.kafkaProducer = new KafkaProducerManager(kafkaBootstrapServers);
        this.storageMonitor = new StorageMonitor(databaseManager, kafkaProducer);
    }

    public void start() {
        LOGGER.info("Starting DB Interface");

        // Start storage monitoring in a separate thread
        Thread monitorThread = new Thread(() -> {
            LOGGER.info("Starting storage level monitor");
            storageMonitor.runMonitoringCycle(10);  // Check every 10 seconds
        }, "StorageMonitorWorker");
        monitorThread.setDaemon(true);
        monitorThread.start();

        LOGGER.info("DB Interface started successfully");
    }

    public static void main(String[] args) {
        String scenarioId = System.getenv("SCENARIO_ID") != null ?
                System.getenv("SCENARIO_ID") : "default";

        String dbUrl = System.getenv("DB_URL") != null ? System.getenv("DB_URL") :
                "jdbc:postgresql://db:5432/mydatabase?user=user&password=password";
        String kafkaBootstrapServers = System.getenv("KAFKA_BOOTSTRAP_SERVERS") != null ?
                System.getenv("KAFKA_BOOTSTRAP_SERVERS") : "kafka:29092";

        LOGGER.info("DbInterface starting with scenarioId: {}", scenarioId);

        DbInterface dbInterface = new DbInterface(dbUrl, kafkaBootstrapServers);
        dbInterface.start();

        // Keep main thread alive
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            LOGGER.error("Main thread interrupted", e);
            Thread.currentThread().interrupt();
        }
    }
}