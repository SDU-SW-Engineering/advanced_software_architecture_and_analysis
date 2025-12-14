
package com.pasta.scheduler.storage;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.scheduler.Scheduler;
import com.pasta.scheduler.enums.BladeType;
import com.pasta.scheduler.kafka.KafkaProducerManager;
import com.pasta.scheduler.machine.MachineManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

public class StorageAlertHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(StorageAlertHandler.class);
    private static final int COOLDOWN_SECONDS = 10;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final Map<String, LocalDateTime> lastAlertTimestamp = new HashMap<>();
    private final Object lock = new Object();

    public void handleStorageAlert(JsonNode alert, MachineManager machineManager,
                                   KafkaProducerManager kafkaProducer, Scheduler scheduler) {
        try {
            String alertId = alert.has("alertId") ? alert.get("alertId").asText() : "unknown";
            long triggerTs = alert.has("triggerTs") ? alert.get("triggerTs").asLong() : System.currentTimeMillis();
            String problemCategory = alert.has("problemCategory") ? alert.get("problemCategory").asText() : "unknown";

            double aFresh = alert.get("aFresh").asDouble();
            double aDry   = alert.get("aDry").asDouble();
            double bFresh = alert.get("bFresh").asDouble();
            double bDry   = alert.get("bDry").asDouble();

            double totalA     = aFresh + aDry;
            double totalB     = bFresh + bDry;
            double totalFresh = aFresh + bFresh;
            double totalDry   = aDry + bDry;

            LOGGER.info("Storage levels - A: {}, B: {}, Fresh: {}, Dry: {}, alertId: {}",
                    String.format("%.2f", totalA), String.format("%.2f", totalB),
                    String.format("%.2f", totalFresh), String.format("%.2f", totalDry), alertId);

            String problem = null;
            double minValue = Math.min(Math.min(totalA, totalB), Math.min(totalFresh, totalDry));
            if (totalA == minValue)      problem = "A";
            else if (totalB == minValue) problem = "B";
            else if (totalFresh == minValue) problem = "fresh";
            else if (totalDry == minValue)   problem = "dry";

            LOGGER.info("Identified problem category: {}", problem);

            if (isOnCooldown(problem)) {
                LOGGER.info("Problem {} is on cooldown, ignoring alert", problem);
                return;
            }
            recordAlert(problem);

            String eventContext = String.format("storageAlert:%s:problem_%s", alertId, problem);
            long reactionTs = System.currentTimeMillis();

            if ("fresh".equals(problem)) {
                handleFreshProblem(totalFresh, totalDry, kafkaProducer, scheduler, eventContext, reactionTs);
            } else if ("dry".equals(problem)) {
                handleDryProblem(totalFresh, totalDry, kafkaProducer, scheduler, eventContext, reactionTs);
            } else if ("A".equals(problem)) {
                handleBladeProblem("A", machineManager, kafkaProducer, eventContext, reactionTs);
            } else if ("B".equals(problem)) {
                handleBladeProblem("B", machineManager, kafkaProducer, eventContext, reactionTs);
            }
        } catch (Exception e) {
            LOGGER.error("Error handling storage alert: {}", e.getMessage(), e);
        }
    }

    private void handleFreshProblem(double totalFresh, double totalDry,
                                    KafkaProducerManager kafkaProducer, Scheduler scheduler,
                                    String eventContext, long reactionTs) {
        int delta = (totalFresh > totalDry / 2.0) ? 2 : 4;
        LOGGER.info("Handling fresh problem: increasing freshAmount by {}, eventContext: {}", delta, eventContext);
        if (isOnCooldown("freshAmount")) {
            LOGGER.info("FreshAmount change on cooldown, skipping");
            return;
        }
        recordAlert("freshAmount");
        scheduler.updateFreshAmount(delta, eventContext, reactionTs);
    }

    private void handleDryProblem(double totalFresh, double totalDry,
                                  KafkaProducerManager kafkaProducer, Scheduler scheduler,
                                  String eventContext, long reactionTs) {
        int delta = (totalFresh > totalDry / 2.0) ? -2 : -4;
        LOGGER.info("Handling dry problem: decreasing freshAmount by {}, eventContext: {}", Math.abs(delta), eventContext);
        if (isOnCooldown("freshAmount")) {
            LOGGER.info("FreshAmount change on cooldown, skipping");
            return;
        }
        recordAlert("freshAmount");
        scheduler.updateFreshAmount(delta, eventContext, reactionTs);
    }

    private void handleBladeProblem(String problemBlade, MachineManager machineManager,
                                    KafkaProducerManager kafkaProducer, String eventContext, long reactionTs) {
        BladeType targetBladeType = "A".equals(problemBlade) ? BladeType.B : BladeType.A;
        LOGGER.info("Handling blade {} problem: looking for machine with blade {}, eventContext: {}",
                problemBlade, targetBladeType.getValue(), eventContext);

        var machineToSwap = machineManager.getAvailableMachines().stream()
                .filter(m -> m.getBladeType() == targetBladeType)
                .max((m1, m2) -> m1.getLastHeartbeat().compareTo(m2.getLastHeartbeat()))
                .orElse(null);

        if (machineToSwap != null) {
            BladeType newBladeType = BladeType.fromString(problemBlade);
            sendBladeSwapCommand(kafkaProducer, machineToSwap.getId(), newBladeType, eventContext, reactionTs);
            LOGGER.info("Sent blade swap for machine {} to blade type {}, eventContext: {}",
                    machineToSwap.getId(), newBladeType.getValue(), eventContext);
        } else {
            LOGGER.warn("No available machine with blade {} to swap for problem {}", targetBladeType.getValue(), problemBlade);
        }
    }

    private void sendBladeSwapCommand(KafkaProducerManager kafkaProducer, int machineId,
                                      BladeType newBladeType, String eventContext, long reactionTs) {
        String message = String.format(
                "{\"title\":\"SwapBlade\",\"machineId\":%d,\"bladeType\":\"%s\",\"eventContext\":\"%s\",\"reactionTs\":%d}",
                machineId, newBladeType.getValue(), eventContext, reactionTs
        );
        kafkaProducer.sendMessage("productionPlan", message);
    }

    private boolean isOnCooldown(String problem) {
        synchronized (lock) {
            LocalDateTime lastTimestamp = lastAlertTimestamp.get(problem);
            if (lastTimestamp == null) return false;
            LocalDateTime cooldownEnd = lastTimestamp.plusSeconds(COOLDOWN_SECONDS);
            return LocalDateTime.now().isBefore(cooldownEnd);
        }
    }

    private void recordAlert(String problem) {
        synchronized (lock) {
            lastAlertTimestamp.put(problem, LocalDateTime.now());
        }
    }
}
