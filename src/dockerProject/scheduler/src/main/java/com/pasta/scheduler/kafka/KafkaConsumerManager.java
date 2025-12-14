package com.pasta.scheduler.kafka;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.scheduler.Scheduler;
import com.pasta.scheduler.machine.MachineManager;
import com.pasta.scheduler.storage.StorageAlertHandler;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

public class KafkaConsumerManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(KafkaConsumerManager.class);

    private final String bootstrapServers;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, Long> currentOffsets = new HashMap<>();
    private final Object offsetLock = new Object();
    private Map<String, Long> savedOffsets = new HashMap<>();

    public KafkaConsumerManager(String bootstrapServers) {
        this.bootstrapServers = bootstrapServers;
    }

    public void setOffsets(Map<String, Long> offsets) {
        this.savedOffsets = offsets != null ? new HashMap<>(offsets) : new HashMap<>();
    }

    public Map<String, Long> getOffsets() {
        synchronized (offsetLock) {
            return new HashMap<>(currentOffsets);
        }
    }

    public void consumeHeartbeats(MachineManager machineManager, KafkaProducerManager kafkaProducer, Scheduler scheduler) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "scheduler-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");

        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(Arrays.asList("heartbeats", "storageAlerts"));
            LOGGER.info("Subscribed to heartbeats and storageAlerts topics");

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

            StorageAlertHandler storageHandler = new StorageAlertHandler();

            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofSeconds(1));

                records.forEach(record -> {
                    try {
                        JsonNode json = objectMapper.readTree(record.value());

                        if ("heartbeats".equals(record.topic())) {
                            handleHeartbeat(json, machineManager, kafkaProducer);
                        } else if ("storageAlerts".equals(record.topic())) {
                            handleStorageAlert(json, machineManager, kafkaProducer, storageHandler, scheduler);
                        }

                        String offsetKey = record.topic() + "-" + record.partition();
                        synchronized (offsetLock) {
                            currentOffsets.put(offsetKey, record.offset());
                        }
                    } catch (Exception e) {
                        LOGGER.error("Error processing message from topic {}: {}",
                                record.topic(), record.value(), e);
                    }
                });
            }
        } catch (Exception e) {
            LOGGER.error("Error in consumer", e);
        }
    }

    private void handleHeartbeat(JsonNode json, MachineManager machineManager,
                                 KafkaProducerManager kafkaProducer) {
        if (json.has("machineId") && json.has("title") &&
                json.get("title").asText().equals("heartbeat")) {

            int machineId = json.get("machineId").asInt();
            String bladeType = json.has("bladeType") ? json.get("bladeType").asText() : null;
            LocalDateTime timestamp = LocalDateTime.now();

            LOGGER.info("Received heartbeat from machine {}", machineId);
            machineManager.addOrUpdateMachineAndSendAssignment(machineId, timestamp, bladeType, kafkaProducer);
        }
    }

    private void handleStorageAlert(JsonNode json, MachineManager machineManager,
                                    KafkaProducerManager kafkaProducer,
                                    StorageAlertHandler storageHandler, Scheduler scheduler) {
        if (json.has("title") && json.get("title").asText().equals("StorageAlert")) {
            // NEW: Extract alertId if present
            String alertId = json.has("alertId") ?
                    json.get("alertId").asText() :
                    "unknown";

            LOGGER.info("Received storage alert: {}", alertId);
            storageHandler.handleStorageAlert(json, machineManager, kafkaProducer, scheduler);
        }
    }
}