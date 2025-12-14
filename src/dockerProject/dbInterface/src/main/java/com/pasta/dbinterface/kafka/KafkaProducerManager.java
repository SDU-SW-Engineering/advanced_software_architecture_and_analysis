package com.pasta.dbinterface.kafka;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

public class KafkaProducerManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(KafkaProducerManager.class);

    private final KafkaProducer<String, String> producer;

    public KafkaProducerManager(String bootstrapServers) {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);

        this.producer = new KafkaProducer<>(props);
    }

    public void sendMessage(String topic, String message) {
        try {
            ProducerRecord<String, String> record = new ProducerRecord<>(topic, message);
            producer.send(record, (metadata, exception) -> {
                if (exception != null) {
                    LOGGER.error("Error sending message to topic " + topic + ": " + exception.getMessage());
                }
            });
        } catch (Exception e) {
            LOGGER.error("Failed to send message: " + e.getMessage());
        }
    }

    public void close() {
        producer.close();
    }
}