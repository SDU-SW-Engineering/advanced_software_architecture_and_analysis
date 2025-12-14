package com.pasta.scheduler.machine;

import com.pasta.scheduler.enums.BladeType;
import java.time.LocalDateTime;

public class Machine {
    private final int id;
    private BladeType bladeType;
    private LocalDateTime lastHeartbeat;

    public Machine(int id, BladeType bladeType) {
        this.id = id;
        this.bladeType = bladeType;
        this.lastHeartbeat = LocalDateTime.now();
    }

    public int getId() {
        return id;
    }

    public BladeType getBladeType() {
        return bladeType;
    }

    public void setBladeType(BladeType bladeType) {
        this.bladeType = bladeType;
    }

    public LocalDateTime getLastHeartbeat() {
        return lastHeartbeat;
    }

    public void setLastHeartbeat(LocalDateTime timestamp) {
        this.lastHeartbeat = timestamp;
    }

    public void setLastHeartbeat() {
        this.lastHeartbeat = LocalDateTime.now();
    }

    public boolean isHealthy(int timeoutSeconds) {
        LocalDateTime cutoff = LocalDateTime.now().minusSeconds(timeoutSeconds);
        return this.lastHeartbeat.isAfter(cutoff);
    }

    @Override
    public String toString() {
        return "Machine{" +
                "id=" + id +
                ", bladeType=" + bladeType +
                ", lastHeartbeat=" + lastHeartbeat +
                '}';
    }
}