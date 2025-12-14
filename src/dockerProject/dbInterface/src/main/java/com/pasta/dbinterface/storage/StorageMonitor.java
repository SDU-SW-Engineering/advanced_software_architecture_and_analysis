// File: dbInterface/src/main/java/com/pasta/dbinterface/storage/StorageMonitor.java

package com.pasta.dbinterface.storage;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.dbinterface.db.DatabaseManager;
import com.pasta.dbinterface.kafka.KafkaProducerManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public class StorageMonitor {
    private static final Logger LOGGER = LoggerFactory.getLogger(StorageMonitor.class);

    private static final double LOW_THRESHOLD = 20.0;
    private static final double HIGH_THRESHOLD = 80.0;
    private static final long MAX_STORAGE_CAPACITY = 100L;

    private final DatabaseManager databaseManager;
    private final KafkaProducerManager kafkaProducer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // Track last sent alert to avoid continuous sends
    private Map<String, Double> lastSentLevels = new HashMap<>();
    private final Object lock = new Object();

    // NEW: Track ongoing storage alert problems by category
    // problemCategory → {alertId, triggerTs, isSolved}
    private Map<String, StorageProblem> ongoingProblems = new HashMap<>();

    private static class StorageProblem {
        String alertId;
        long triggerTs;
        boolean isSolved;
        String problemCategory;

        StorageProblem(String alertId, long triggerTs, String problemCategory) {
            this.alertId = alertId;
            this.triggerTs = triggerTs;
            this.problemCategory = problemCategory;
            this.isSolved = false;
        }
    }

    public StorageMonitor(DatabaseManager databaseManager, KafkaProducerManager kafkaProducer) {
        this.databaseManager = databaseManager;
        this.kafkaProducer = kafkaProducer;
    }

    public void runMonitoringCycle(int intervalSeconds) {
        while (true) {
            try {
                checkStorageLevels();
                Thread.sleep(intervalSeconds * 1000L);
            } catch (InterruptedException e) {
                LOGGER.error("Monitoring cycle interrupted", e);
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void checkStorageLevels() {
        Map<String, Double> storageLevels = new HashMap<>();
        boolean thresholdViolated = false;

        // Check all four combinations
        double aFresh = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("A", true));
        double aDry = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("A", false));
        double bFresh = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("B", true));
        double bDry = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("B", false));

        storageLevels.put("aFresh", aFresh);
        storageLevels.put("aDry", aDry);
        storageLevels.put("bFresh", bFresh);
        storageLevels.put("bDry", bDry);

        // Check if any threshold is violated
        if (isThresholdViolated(aFresh) || isThresholdViolated(aDry) ||
                isThresholdViolated(bFresh) || isThresholdViolated(bDry)) {
            thresholdViolated = true;
        }

        // NEW: Update problem solved status
        updateProblemStatus(storageLevels);

        // Send alert only if threshold violated AND levels have changed since last alert
        // AND there's no unsolved problem with the same category
        if (thresholdViolated && hasLevelsChanged(storageLevels)) {
            String problemCategory = identifyProblemCategory(storageLevels);

            // Check if this problem category already has an unsolved event
            if (!hasUnsolvedProblem(problemCategory)) {
                sendStorageAlert(storageLevels, problemCategory);
            } else {
                LOGGER.debug("Problem {} already has unsolved event, skipping duplicate alert", problemCategory);
            }
        }
    }

    private double calculateStorageLevel(long totalStock) {
        return (totalStock / (double) MAX_STORAGE_CAPACITY) * 100.0;
    }

    private boolean isThresholdViolated(double level) {
        return level < LOW_THRESHOLD || level > HIGH_THRESHOLD;
    }

    private boolean hasLevelsChanged(Map<String, Double> currentLevels) {
        synchronized (lock) {
            if (lastSentLevels.isEmpty()) {
                return true;  // First alert
            }

            // Check if any level has significantly changed (more than 1% difference)
            for (String key : currentLevels.keySet()) {
                Double lastLevel = lastSentLevels.get(key);
                if (lastLevel == null) {
                    return true;
                }
                if (Math.abs(currentLevels.get(key) - lastLevel) > 1.0) {
                    return true;
                }
            }
            return false;
        }
    }

    // NEW: Identify which problem category (A, B, fresh, dry) is lowest
    private String identifyProblemCategory(Map<String, Double> storageLevels) {
        double aFresh = storageLevels.get("aFresh");
        double aDry = storageLevels.get("aDry");
        double bFresh = storageLevels.get("bFresh");
        double bDry = storageLevels.get("bDry");

        double totalA = aFresh + aDry;
        double totalB = bFresh + bDry;
        double totalFresh = aFresh + bFresh;
        double totalDry = aDry + bDry;

        double minValue = Math.min(Math.min(totalA, totalB), Math.min(totalFresh, totalDry));

        if (totalA == minValue) return "A";
        if (totalB == minValue) return "B";
        if (totalFresh == minValue) return "fresh";
        if (totalDry == minValue) return "dry";

        return "unknown";
    }

    // NEW: Check if a problem category already has an unsolved event
    private boolean hasUnsolvedProblem(String problemCategory) {
        synchronized (lock) {
            StorageProblem problem = ongoingProblems.get(problemCategory);
            return problem != null && !problem.isSolved;
        }
    }

    // NEW: Update status of ongoing problems
    private void updateProblemStatus(Map<String, Double> storageLevels) {
        synchronized (lock) {
            // Check each problem category
            for (String category : new String[]{"A", "B", "fresh", "dry"}) {
                StorageProblem problem = ongoingProblems.get(category);
                if (problem != null && !problem.isSolved) {
                    // Check if this problem is resolved (all levels back in safe zone)
                    boolean isSafe = true;
                    double aFresh = storageLevels.get("aFresh");
                    double aDry = storageLevels.get("aDry");
                    double bFresh = storageLevels.get("bFresh");
                    double bDry = storageLevels.get("bDry");

                    if (isThresholdViolated(aFresh) || isThresholdViolated(aDry) ||
                            isThresholdViolated(bFresh) || isThresholdViolated(bDry)) {
                        isSafe = false;
                    }

                    if (isSafe) {
                        problem.isSolved = true;
                        LOGGER.info("Storage problem {} resolved (alertId: {})", category, problem.alertId);
                    }
                }
            }
        }
    }

    private void sendStorageAlert(Map<String, Double> storageLevels, String problemCategory) {
        try {
            String alertId = UUID.randomUUID().toString();
            long triggerTs = System.currentTimeMillis();

            synchronized (lock) {
                // Update last sent levels
                lastSentLevels.putAll(storageLevels);

                // Track this new problem
                ongoingProblems.put(problemCategory, new StorageProblem(alertId, triggerTs, problemCategory));
            }

            Map<String, Object> message = new HashMap<>();
            message.put("title", "StorageAlert");
            message.put("alertId", alertId);  // NEW
            message.put("triggerTs", triggerTs);  // NEW
            message.put("problemCategory", problemCategory);  // NEW
            message.put("aFresh", Math.round(storageLevels.get("aFresh") * 100.0) / 100.0);
            message.put("aDry", Math.round(storageLevels.get("aDry") * 100.0) / 100.0);
            message.put("bFresh", Math.round(storageLevels.get("bFresh") * 100.0) / 100.0);
            message.put("bDry", Math.round(storageLevels.get("bDry") * 100.0) / 100.0);

            String jsonMessage = objectMapper.writeValueAsString(message);
            kafkaProducer.sendMessage("storageAlerts", jsonMessage);

            LOGGER.info("Storage alert sent: alertId={}, problemCategory={}, triggerTs={}, aFresh={}, aDry={}, bFresh={}, bDry={}",
                    alertId, problemCategory, triggerTs,
                    storageLevels.get("aFresh"), storageLevels.get("aDry"),
                    storageLevels.get("bFresh"), storageLevels.get("bDry"));
        } catch (Exception e) {
            LOGGER.error("Error sending storage alert: " + e.getMessage());
        }
    }
}