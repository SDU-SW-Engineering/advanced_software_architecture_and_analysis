package dk.sdu.odense.tek.asaa.subsystem;

public enum State {
    OFF(0),
    RUNNING(1),
    IDLE(2),
    ERROR(3),
    UNKNOWN(4);

    private final int code;

    State(int code) {
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
