package com.pasta.sortingsubsystem;

import com.pasta.sortingsubsystem.kafka.KafkaConsumerManager;
import com.pasta.sortingsubsystem.kafka.KafkaProducerManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class SortingSubsystem {
    private static final Logger LOGGER = LoggerFactory.getLogger(SortingSubsystem.class);

    private final KafkaConsumerManager kafkaConsumer;
    private final KafkaProducerManager kafkaProducer;
    private final FreshAmountManager freshAmountManager;

    public SortingSubsystem(String kafkaBootstrapServers) {
        this.kafkaConsumer = new KafkaConsumerManager(kafkaBootstrapServers);
        this.kafkaProducer = new KafkaProducerManager(kafkaBootstrapServers);
        this.freshAmountManager = new FreshAmountManager(kafkaProducer);
    }

    public void start() {
        LOGGER.info("Starting Sorting Subsystem");

        // Start consumer thread to listen for ChangeFreshAmount messages
        Thread consumerThread = new Thread(() -> {
            LOGGER.info("Starting productionPlan consumer");
            kafkaConsumer.consumeProductionPlan(freshAmountManager);
        }, "ProductionPlanConsumerWorker");
        consumerThread.setDaemon(true);
        consumerThread.start();

        LOGGER.info("Sorting Subsystem started successfully");
    }

    public static void main(String[] args) {
        String kafkaBootstrapServers = "kafka:29092";
        SortingSubsystem sortingSubsystem = new SortingSubsystem(kafkaBootstrapServers);
        sortingSubsystem.start();

        // Keep main thread alive
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            LOGGER.error("Main thread interrupted", e);
            Thread.currentThread().interrupt();
        }
    }
}