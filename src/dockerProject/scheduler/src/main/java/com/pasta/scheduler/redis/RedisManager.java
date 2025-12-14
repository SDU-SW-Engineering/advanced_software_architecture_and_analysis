
package com.pasta.scheduler.redis;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.params.SetParams;

import java.util.HashMap;
import java.util.Map;

public class RedisManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(RedisManager.class);

    private static final String ACTIVE_SCHEDULER_KEY = "active_scheduler";
    private static final String MACHINES_KEY         = "scheduler:machines";
    private static final String ASSIGNED_KEY         = "scheduler:assigned";      // NEW
    private static final String FRESH_AMOUNT_KEY     = "scheduler:freshAmount";
    private static final String KAFKA_OFFSETS_KEY    = "scheduler:kafka_offsets";

    private static final int LEASE_DURATION_SECONDS = 5;

    private final JedisPool jedisPool;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public RedisManager(String host, int port) {
        this.jedisPool = new JedisPool(host, port);
        LOGGER.info("RedisManager initialized with {}:{}", host, port);
    }

    public boolean becomeActiveScheduler(String schedulerId) {
        try (Jedis jedis = jedisPool.getResource()) {
            SetParams params = new SetParams().nx().ex(LEASE_DURATION_SECONDS);
            String result = jedis.set(ACTIVE_SCHEDULER_KEY, schedulerId, params);
            boolean success = result != null && result.equals("OK");
            if (success) {
                LOGGER.info("Became active scheduler");
            }
            return success;
        } catch (Exception e) {
            LOGGER.error("Error in leadership election: {}", e.getMessage(), e);
            return false;
        }
    }

    public String getActiveScheduler() {
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.get(ACTIVE_SCHEDULER_KEY);
        } catch (Exception e) {
            LOGGER.error("Error getting active scheduler: {}", e.getMessage(), e);
            return null;
        }
    }

    public void saveMachines(String machinesJson) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.set(MACHINES_KEY, machinesJson);
        } catch (Exception e) {
            LOGGER.error("Error saving machines to Redis: {}", e.getMessage(), e);
        }
    }

    public String getMachines() {
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.get(MACHINES_KEY);
        } catch (Exception e) {
            LOGGER.error("Error loading machines from Redis: {}", e.getMessage(), e);
            return null;
        }
    }

    // NEW: assignedMachines persistence
    public void saveAssignedMachines(String assignedJson) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.set(ASSIGNED_KEY, assignedJson);
        } catch (Exception e) {
            LOGGER.error("Error saving assignedMachines to Redis: {}", e.getMessage(), e);
        }
    }

    public String getAssignedMachines() {
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.get(ASSIGNED_KEY);
        } catch (Exception e) {
            LOGGER.error("Error loading assignedMachines from Redis: {}", e.getMessage(), e);
            return null;
        }
    }

    public void setFreshAmount(int amount) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.set(FRESH_AMOUNT_KEY, String.valueOf(amount));
        } catch (Exception e) {
            LOGGER.error("Error saving freshAmount to Redis: {}", e.getMessage(), e);
        }
    }

    public Integer getFreshAmount() {
        try (Jedis jedis = jedisPool.getResource()) {
            String value = jedis.get(FRESH_AMOUNT_KEY);
            if (value != null) {
                return Integer.parseInt(value);
            }
            return null;
        } catch (Exception e) {
            LOGGER.error("Error loading freshAmount from Redis: {}", e.getMessage(), e);
            return null;
        }
    }

    public void setKafkaOffsets(Map<String, Long> offsets) {
        try (Jedis jedis = jedisPool.getResource()) {
            if (offsets == null || offsets.isEmpty()) {
                return;
            }
            jedis.del(KAFKA_OFFSETS_KEY);
            for (Map.Entry<String, Long> entry : offsets.entrySet()) {
                jedis.hset(KAFKA_OFFSETS_KEY, entry.getKey(), entry.getValue().toString());
            }
        } catch (Exception e) {
            LOGGER.error("Error saving Kafka offsets to Redis: {}", e.getMessage(), e);
        }
    }

    public Map<String, Long> getKafkaOffsets() {
        try (Jedis jedis = jedisPool.getResource()) {
            Map<String, String> offsetMap = jedis.hgetAll(KAFKA_OFFSETS_KEY);
            Map<String, Long> result = new HashMap<>();
            for (Map.Entry<String, String> entry : offsetMap.entrySet()) {
                try {
                    result.put(entry.getKey(), Long.parseLong(entry.getValue()));
                } catch (NumberFormatException e) {
                    LOGGER.warn("Invalid offset value for {}: {}", entry.getKey(), entry.getValue());
                }
            }
            return result;
        } catch (Exception e) {
            LOGGER.error("Error loading Kafka offsets from Redis: {}", e.getMessage(), e);
            return new HashMap<>();
        }
    }

    public void close() {
        jedisPool.close();
        LOGGER.info("RedisManager connection closed");
    }
}
