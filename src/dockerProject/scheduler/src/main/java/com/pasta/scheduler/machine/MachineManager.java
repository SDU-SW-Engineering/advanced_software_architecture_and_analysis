package com.pasta.scheduler.machine;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.scheduler.enums.BladeType;
import com.pasta.scheduler.kafka.KafkaProducerManager;
import com.pasta.scheduler.redis.RedisManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class MachineManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(MachineManager.class);
    private static final int HEARTBEAT_TIMEOUT_SECONDS = 10;
    private static final int HEALTH_CHECK_INTERVAL_SECONDS = 5;
    private static final long DISCOVERY_PHASE_DURATION_MS = 12000;

    private final List<Machine> availableMachines = new ArrayList<>();
    private final Object lock = new Object();
    private final long startTime = System.currentTimeMillis();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private boolean needsRedisUpdate = false;

    public boolean isDiscoveryPhaseComplete() {
        return (System.currentTimeMillis() - startTime) > DISCOVERY_PHASE_DURATION_MS;
    }

    public void addOrUpdateMachineAndSendAssignment(int machineId, LocalDateTime heartbeatTimestamp,
                                                    String bladeTypeFromHeartbeat,
                                                    KafkaProducerManager kafkaProducer) {
        synchronized (lock) {
            Machine existingMachine = availableMachines.stream()
                    .filter(m -> m.getId() == machineId)
                    .findFirst()
                    .orElse(null);

            // CASE 1: Machine exists and has a blade type - just update heartbeat
            if (existingMachine != null && bladeTypeFromHeartbeat != null) {
                existingMachine.setLastHeartbeat(heartbeatTimestamp);
                LOGGER.debug("Updated heartbeat for working machine {}", machineId);
                return;
            }

            // CASE 2: Machine exists but heartbeat has no blade type
            // This means machine was restarted and is waiting for assignment
            if (existingMachine != null && bladeTypeFromHeartbeat == null) {
                existingMachine.setLastHeartbeat(heartbeatTimestamp);
                LOGGER.info("Machine {} is waiting for assignment, resending AssignBlade with blade type {}",
                        machineId, existingMachine.getBladeType().getValue());

                // Always resend AssignBlade when machine is waiting
                sendAssignBladeCommand(kafkaProducer, machineId, existingMachine.getBladeType());
                return;
            }

            // CASE 3: New machine with blade type (recovered from Redis or another scheduler)
            if (bladeTypeFromHeartbeat != null) {
                BladeType bladeType = BladeType.fromString(bladeTypeFromHeartbeat);
                Machine newMachine = new Machine(machineId, bladeType);
                newMachine.setLastHeartbeat(heartbeatTimestamp);
                availableMachines.add(newMachine);
                needsRedisUpdate = true;
                LOGGER.info("New machine {} registered with existing blade type {}", machineId, bladeType.getValue());
                return;
            }

            // CASE 4: Completely new machine without blade type
            BladeType bladeType = determineBladeTypeForNewMachine();
            Machine newMachine = new Machine(machineId, bladeType);
            newMachine.setLastHeartbeat(heartbeatTimestamp);
            availableMachines.add(newMachine);
            needsRedisUpdate = true;

            LOGGER.info("New machine {} created with assigned blade type {}", machineId, bladeType.getValue());

            // Send AssignBlade immediately after discovery phase
            if (isDiscoveryPhaseComplete()) {
                sendAssignBladeCommand(kafkaProducer, machineId, bladeType);
            } else {
                LOGGER.debug("Discovery phase in progress - delaying AssignBlade for machine {}", machineId);
            }
        }
    }

    private BladeType determineBladeTypeForNewMachine() {
        synchronized (lock) {
            long countA = availableMachines.stream()
                    .filter(m -> m.getBladeType() == BladeType.A)
                    .count();
            long countB = availableMachines.stream()
                    .filter(m -> m.getBladeType() == BladeType.B)
                    .count();

            return countA <= countB ? BladeType.A : BladeType.B;
        }
    }

    public void startHealthCheck(KafkaProducerManager kafkaProducer) {
        while (true) {
            try {
                Thread.sleep(HEALTH_CHECK_INTERVAL_SECONDS * 1000L);
                checkMachineHealth(kafkaProducer);
            } catch (InterruptedException e) {
                LOGGER.error("Health check interrupted", e);
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void checkMachineHealth(KafkaProducerManager kafkaProducer) {
        synchronized (lock) {
            List<Machine> unhealthyMachines = availableMachines.stream()
                    .filter(m -> !m.isHealthy(HEARTBEAT_TIMEOUT_SECONDS))
                    .collect(Collectors.toList());

            for (Machine unhealthyMachine : unhealthyMachines) {
                LOGGER.warn("Machine {} is unhealthy (last heartbeat: {})",
                        unhealthyMachine.getId(), unhealthyMachine.getLastHeartbeat());

                BladeType failedBladeType = unhealthyMachine.getBladeType();
                BladeType otherBladeType = failedBladeType == BladeType.A ? BladeType.B : BladeType.A;

                long countFailedBlade = availableMachines.stream()
                        .filter(m -> m.getBladeType() == failedBladeType && m.getId() != unhealthyMachine.getId())
                        .count();

                long countOtherBlade = availableMachines.stream()
                        .filter(m -> m.getBladeType() == otherBladeType)
                        .count();

                availableMachines.remove(unhealthyMachine);
                needsRedisUpdate = true;
                LOGGER.info("Removed unhealthy machine {}", unhealthyMachine.getId());

                if (countFailedBlade < countOtherBlade - 1) {
                    LOGGER.info("Blade swap needed: {} machines with {}, {} machines with {}",
                            countFailedBlade, failedBladeType, countOtherBlade, otherBladeType);

                    Machine machineToSwap = availableMachines.stream()
                            .filter(m -> m.getBladeType() == otherBladeType)
                            .max((m1, m2) -> m1.getLastHeartbeat().compareTo(m2.getLastHeartbeat()))
                            .orElse(null);

                    if (machineToSwap != null) {
                        String eventContext = String.format("machineFailure:machine_%d", unhealthyMachine.getId());
                        long reactionTs = System.currentTimeMillis();
                        sendBladeSwapCommand(kafkaProducer, machineToSwap.getId(), failedBladeType,
                                eventContext, reactionTs);
                    }
                }
            }
        }
    }

    private void sendBladeSwapCommand(KafkaProducerManager kafkaProducer, int machineId,
                                      BladeType newBladeType, String eventContext, long reactionTs) {
        String message = String.format(
                "{\"title\":\"SwapBlade\"," +
                        "\"machineId\":%d," +
                        "\"bladeType\":\"%s\"," +
                        "\"eventContext\":\"%s\"," +
                        "\"reactionTs\":%d}",
                machineId,
                newBladeType.getValue(),
                eventContext,
                reactionTs
        );
        kafkaProducer.sendMessage("productionPlan", message);
        LOGGER.info("Sent blade swap command for machine {} to blade type {}, eventContext: {}",
                machineId, newBladeType, eventContext);
    }

    private void sendBladeSwapCommand(KafkaProducerManager kafkaProducer, int machineId, BladeType newBladeType) {
        String eventContext = "initialization:initial_discovery";
        long reactionTs = System.currentTimeMillis();
        sendBladeSwapCommand(kafkaProducer, machineId, newBladeType, eventContext, reactionTs);
    }

    private void sendAssignBladeCommand(KafkaProducerManager kafkaProducer, int machineId, BladeType bladeType) {
        String message = String.format(
                "{\"title\":\"AssignBlade\",\"machineId\":%d,\"bladeType\":\"%s\"}",
                machineId,
                bladeType.getValue()
        );
        kafkaProducer.sendMessage("productionPlan", message);
        LOGGER.info("Sent AssignBlade command for machine {} with blade type {}", machineId, bladeType);
    }

    public void saveToRedis(RedisManager redisManager) {
        synchronized (lock) {
            if (!needsRedisUpdate) {
                return;
            }

            try {
                String machinesJson = objectMapper.writeValueAsString(availableMachines);
                redisManager.saveMachines(machinesJson);
                needsRedisUpdate = false;
                LOGGER.debug("Saved machine state to Redis");
            } catch (Exception e) {
                LOGGER.error("Error serializing machines to Redis: {}", e.getMessage(), e);
            }
        }
    }

    public void loadFromRedis(RedisManager redisManager) {
        synchronized (lock) {
            try {
                String machinesJson = redisManager.getMachines();
                if (machinesJson != null && !machinesJson.isEmpty()) {
                    Machine[] machines = objectMapper.readValue(machinesJson, Machine[].class);
                    availableMachines.clear();
                    availableMachines.addAll(Arrays.asList(machines));
                    needsRedisUpdate = false;
                    LOGGER.info("Loaded {} machines from Redis", machines.length);
                } else {
                    LOGGER.info("No machines found in Redis, starting fresh");
                }
            } catch (Exception e) {
                LOGGER.error("Error deserializing machines from Redis: {}", e.getMessage(), e);
            }
        }
    }

    public List<Machine> getAvailableMachines() {
        synchronized (lock) {
            return new ArrayList<>(availableMachines);
        }
    }

    public void printStatus() {
        synchronized (lock) {
            LOGGER.info("=== Machine Status ===");
            LOGGER.info("Total machines: {}", availableMachines.size());
            long countA = availableMachines.stream().filter(m -> m.getBladeType() == BladeType.A).count();
            long countB = availableMachines.stream().filter(m -> m.getBladeType() == BladeType.B).count();
            LOGGER.info("Blade A: {}, Blade B: {}", countA, countB);
            availableMachines.forEach(m -> LOGGER.info("  {}", m));
        }
    }
}