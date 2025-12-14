
package com.pasta.scheduler;

import com.pasta.scheduler.kafka.KafkaConsumerManager;
import com.pasta.scheduler.kafka.KafkaProducerManager;
import com.pasta.scheduler.machine.MachineManager;
import com.pasta.scheduler.redis.RedisManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Scheduler {
    private static final Logger LOGGER = LoggerFactory.getLogger(Scheduler.class);

    private static final int INITIAL_FRESH_AMOUNT = 4;
    private static final String SCHEDULER_ID = "primary";
    private static final int REDIS_PERSIST_INTERVAL_SECONDS = 5;

    // NEW: cooldown to avoid repeated init change spam after reload/leadership renewal
    private static final long INIT_CHANGE_COOLDOWN_MS = 30_000;

    private final MachineManager machineManager;
    private final KafkaConsumerManager kafkaConsumer;
    private final KafkaProducerManager kafkaProducer;
    private final RedisManager redisManager;

    private int freshAmount;
    private int lastSentFreshAmount;
    private boolean isActive = false;

    // NEW: track last init ChangeFreshAmount emission time
    private long lastInitChangeSentAt = 0L;

    public Scheduler(String kafkaBootstrapServers, String redisHost, int redisPort) {
        this.machineManager = new MachineManager();
        this.kafkaConsumer = new KafkaConsumerManager(kafkaBootstrapServers);
        this.kafkaProducer = new KafkaProducerManager(kafkaBootstrapServers);
        this.redisManager = new RedisManager(redisHost, redisPort);
        this.freshAmount = INITIAL_FRESH_AMOUNT;
        this.lastSentFreshAmount = -1;

        LOGGER.info("Scheduler initialized with Kafka: {}, Redis: {}:{}", kafkaBootstrapServers, redisHost, redisPort);
    }

    public void start() {
        LOGGER.info("Starting Scheduler");
        // Attempt leader election via Redis
        if (!attemptLeaderElection()) {
            LOGGER.warn("Failed to become active scheduler, but continuing as standby...");
        }

        // Load persisted state from Redis if available
        loadStateFromRedis();

        // Send initial ChangeFreshAmount message (with cooldown + idempotence)
        sendChangeFreshAmountMessage(freshAmount);

        // Start Kafka consumer
        Thread consumerThread = new Thread(() -> {
            LOGGER.info("Starting Kafka consumer");
            kafkaConsumer.consumeHeartbeats(machineManager, kafkaProducer, this);
        }, "KafkaConsumerWorker");
        consumerThread.setDaemon(true);
        consumerThread.start();

        // Start machine health checker
        Thread healthCheckThread = new Thread(() -> {
            try {
                LOGGER.info("Waiting 10 seconds for initial machine discovery...");
                Thread.sleep(10_000);
                LOGGER.info("Starting machine health checker");
                machineManager.startHealthCheck(kafkaProducer);
            } catch (InterruptedException e) {
                LOGGER.error("Health check thread interrupted", e);
                Thread.currentThread().interrupt();
            }
        }, "MachineHealthCheckerWorker");
        healthCheckThread.setDaemon(true);
        healthCheckThread.start();

        // Start Redis state persistence
        Thread redisPersistThread = new Thread(() -> {
            try {
                LOGGER.info("Waiting before starting Redis persistence...");
                Thread.sleep(5_000);
                LOGGER.info("Starting Redis state persistence");
                persistStateToRedisLoop();
            } catch (InterruptedException e) {
                LOGGER.error("Redis persist thread interrupted", e);
                Thread.currentThread().interrupt();
            }
        }, "RedisPersistWorker");
        redisPersistThread.setDaemon(true);
        redisPersistThread.start();

        // Start leader renewal
        Thread leaderRenewalThread = new Thread(() -> {
            try {
                Thread.sleep(2000);
                LOGGER.info("Starting leader election renewal");
                renewLeadershipLoop();
            } catch (InterruptedException e) {
                LOGGER.error("Leader renewal thread interrupted", e);
                Thread.currentThread().interrupt();
            }
        }, "LeaderRenewalWorker");
        leaderRenewalThread.setDaemon(true);
        leaderRenewalThread.start();

        LOGGER.info("Scheduler started successfully with freshAmount={}", freshAmount);
    }

    private boolean attemptLeaderElection() {
        try {
            boolean success = redisManager.becomeActiveScheduler(SCHEDULER_ID);
            if (success) {
                isActive = true;
                LOGGER.info("✅ Became ACTIVE scheduler");
            } else {
                isActive = false;
                LOGGER.warn("⚠️ Another scheduler is active, running as STANDBY");
            }
            return success;
        } catch (Exception e) {
            LOGGER.error("Error during leader election: {}", e.getMessage(), e);
            return false;
        }
    }

    private void renewLeadershipLoop() {
        while (true) {
            try {
                Thread.sleep(3000); // Renew every 3 seconds (lease is 5 seconds)
                if (isActive) {
                    boolean stillActive = redisManager.becomeActiveScheduler(SCHEDULER_ID);
                    if (!stillActive) {
                        LOGGER.warn("Lost leadership, transitioning to STANDBY");
                        isActive = false;
                    } else {
                        LOGGER.debug("✓ Leadership renewed");
                    }
                } else {
                    boolean acquired = redisManager.becomeActiveScheduler(SCHEDULER_ID);
                    if (acquired) {
                        LOGGER.info("✅ Acquired leadership, transitioning to ACTIVE");
                        isActive = true;
                        loadStateFromRedis(); // reload when becoming active
                    }
                }
            } catch (Exception e) {
                LOGGER.error("Error in leadership renewal: {}", e.getMessage());
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private void persistStateToRedisLoop() {
        while (true) {
            try {
                Thread.sleep(REDIS_PERSIST_INTERVAL_SECONDS * 1000);
                if (isActive) {
                    machineManager.saveToRedis(redisManager);
                    redisManager.setFreshAmount(freshAmount);
                    redisManager.setKafkaOffsets(kafkaConsumer.getOffsets());
                    LOGGER.debug("State persisted to Redis");
                } else {
                    LOGGER.debug("Standby scheduler, skipping Redis persistence");
                }
            } catch (Exception e) {
                LOGGER.error("Error persisting state to Redis: {}", e.getMessage(), e);
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private void loadStateFromRedis() {
        try {
            LOGGER.info("Loading scheduler state from Redis...");
            machineManager.loadFromRedis(redisManager);

            Integer savedFreshAmount = redisManager.getFreshAmount();
            if (savedFreshAmount != null) {
                // NEW: only force resend if the persisted value differs from what we last sent
                freshAmount = savedFreshAmount;
                if (lastSentFreshAmount != freshAmount) {
                    lastSentFreshAmount = -1; // force next send
                    LOGGER.info("Loaded freshAmount from Redis (will re-send): {}", freshAmount);
                } else {
                    LOGGER.info("Loaded freshAmount from Redis (unchanged, no resend): {}", freshAmount);
                }
            }

            kafkaConsumer.setOffsets(redisManager.getKafkaOffsets());
            LOGGER.info("✓ State loaded from Redis");
        } catch (Exception e) {
            LOGGER.error("Error loading state from Redis: {}", e.getMessage(), e);
            LOGGER.info("Starting with default state");
        }
    }

    public synchronized void updateFreshAmount(int delta, String eventContext, long reactionTs) {
        int newFreshAmount = freshAmount + delta;
        if (newFreshAmount < 0) {
            newFreshAmount = 0;
            LOGGER.warn("freshAmount would be negative, clamped to 0");
        } else if (newFreshAmount > 10) {
            newFreshAmount = 10;
            LOGGER.warn("freshAmount would exceed 10, clamped to 10");
        }

        // NEW: idempotence — skip if effective value unchanged
        if (newFreshAmount == freshAmount && newFreshAmount == lastSentFreshAmount) {
            LOGGER.debug("freshAmount unchanged ({}), skipping message", newFreshAmount);
            return;
        }

        freshAmount = newFreshAmount;
        LOGGER.info("Updated freshAmount: {} (delta: {}, eventContext: {})", freshAmount, delta, eventContext);
        sendChangeFreshAmountMessage(freshAmount, eventContext, reactionTs);
        redisManager.setFreshAmount(freshAmount); // persist immediately
    }

    private void sendChangeFreshAmountMessage(int amount, String eventContext, long reactionTs) {
        // Only send if value has actually changed
        if (amount == lastSentFreshAmount) {
            LOGGER.debug("freshAmount unchanged ({}), skipping message", amount);
            return;
        }
        lastSentFreshAmount = amount;

        String message = String.format(
                "{\"title\":\"ChangeFreshAmount\",\"freshAmount\":%d,\"eventContext\":\"%s\",\"reactionTs\":%d}",
                amount, eventContext, reactionTs
        );
        kafkaProducer.sendMessage("productionPlan", message);
        LOGGER.info("Sent ChangeFreshAmount message with freshAmount={}, eventContext={}", amount, eventContext);
    }

    public synchronized void sendChangeFreshAmountMessage(int amount) {
        // Initialization path: add a small cooldown to avoid repeated init spam on reloads
        long now = System.currentTimeMillis();
        if (amount == lastSentFreshAmount && (now - lastInitChangeSentAt) < INIT_CHANGE_COOLDOWN_MS) {
            LOGGER.debug("Skipping init ChangeFreshAmount: same value {} within cooldown {}ms", amount, INIT_CHANGE_COOLDOWN_MS);
            return;
        }
        lastInitChangeSentAt = now;

        String eventContext = "initialization:startup";
        long reactionTs = System.currentTimeMillis();
        sendChangeFreshAmountMessage(amount, eventContext, reactionTs);
    }

    public int getFreshAmount() {
        return freshAmount;
    }

    public boolean isActive() {
        return isActive;
    }

    public static void main(String[] args) {
        String kafkaBootstrapServers = System.getenv("KAFKA_BOOTSTRAP_SERVERS") != null ?
                System.getenv("KAFKA_BOOTSTRAP_SERVERS") : "kafka:29092";
        String redisHost = System.getenv("REDIS_HOST") != null ?
                System.getenv("REDIS_HOST") : "redis";
        int redisPort = System.getenv("REDIS_PORT") != null ?
                Integer.parseInt(System.getenv("REDIS_PORT")) : 6379;

        Scheduler scheduler = new Scheduler(kafkaBootstrapServers, redisHost, redisPort);
        scheduler.start();

        // Keep main thread alive
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            LOGGER.error("Main thread interrupted", e);
            Thread.currentThread().interrupt();
        }
    }
}
