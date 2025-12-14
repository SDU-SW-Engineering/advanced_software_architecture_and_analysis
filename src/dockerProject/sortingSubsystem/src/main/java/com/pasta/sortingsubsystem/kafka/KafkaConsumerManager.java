package com.pasta.sortingsubsystem.kafka;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.sortingsubsystem.FreshAmountManager;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.Collections;
import java.util.Properties;

public class KafkaConsumerManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(KafkaConsumerManager.class);

    private final String bootstrapServers;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public KafkaConsumerManager(String bootstrapServers) {
        this.bootstrapServers = bootstrapServers;
    }

    public void consumeProductionPlan(FreshAmountManager freshAmountManager) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "sorting-subsystem-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");

        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(Collections.singleton("productionPlan"));
            LOGGER.info("Subscribed to productionPlan topic");

            // Wait for initial partition assignment
            boolean assigned = false;
            int attempts = 0;
            while (!assigned && attempts < 10) {
                consumer.poll(Duration.ofMillis(100));
                assigned = !consumer.assignment().isEmpty();
                if (!assigned) {
                    attempts++;
                    Thread.sleep(200);
                }
            }
            LOGGER.info("Consumer ready, assignment: {}", consumer.assignment());

            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));

                records.forEach(record -> {
                    try {
                        JsonNode json = objectMapper.readTree(record.value());

                        if (json.has("title") &&
                                json.get("title").asText().equals("ChangeFreshAmount")) {
                            LOGGER.info("Received ChangeFreshAmount message");
                            freshAmountManager.handleChangeFreshAmount(json);
                        }
                    } catch (Exception e) {
                        LOGGER.error("Error processing message: {}", record.value(), e);
                    }
                });
            }
        } catch (Exception e) {
            LOGGER.error("Error in productionPlan consumer", e);
        }
    }
}