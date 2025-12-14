package com.pasta.scheduler.enums;

public enum BladeType {
    A("A"),
    B("B");

    private final String value;

    BladeType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static BladeType fromString(String value) {
        for (BladeType type : BladeType.values()) {
            if (type.value.equalsIgnoreCase(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Invalid BladeType: " + value);
    }
}