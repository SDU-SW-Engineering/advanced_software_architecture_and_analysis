package com.pasta.sortingsubsystem;

import com.fasterxml.jackson.databind.JsonNode;
import com.pasta.sortingsubsystem.kafka.KafkaProducerManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class FreshAmountManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(FreshAmountManager.class);

    private int freshAmount;
    private final KafkaProducerManager kafkaProducer;
    private final Object lock = new Object();

    public FreshAmountManager(KafkaProducerManager kafkaProducer) {
        this.kafkaProducer = kafkaProducer;
        this.freshAmount = 4;  // Default value
        LOGGER.info("Initialized FreshAmountManager with freshAmount={}", freshAmount);
    }

    public void handleChangeFreshAmount(JsonNode message) {
        if (!message.has("freshAmount")) {
            LOGGER.warn("ChangeFreshAmount message missing freshAmount field");
            return;
        }

        int newFreshAmount = message.get("freshAmount").asInt();

        // Clamp freshAmount between 0 and 10
        if (newFreshAmount < 0) {
            newFreshAmount = 0;
            LOGGER.warn("freshAmount would be negative, clamped to 0");
        } else if (newFreshAmount > 10) {
            newFreshAmount = 10;
            LOGGER.warn("freshAmount would exceed 10, clamped to 10");
        }

        synchronized (lock) {
            int oldFreshAmount = freshAmount;
            freshAmount = newFreshAmount;
            LOGGER.info("Updated freshAmount: {} -> {}", oldFreshAmount, newFreshAmount);
        }

        // Send confirmation message
        sendFreshAmountChangedMessage(newFreshAmount);
    }

    private void sendFreshAmountChangedMessage(int freshAmount) {
        String message = String.format(
                "{\"title\":\"FreshAmountChanged\",\"freshAmount\":%d}",
                freshAmount
        );
        kafkaProducer.sendMessage("productionPlan", message);
        LOGGER.info("Sent FreshAmountChanged message with freshAmount={}", freshAmount);
    }

    public synchronized int getFreshAmount() {
        return freshAmount;
    }
}