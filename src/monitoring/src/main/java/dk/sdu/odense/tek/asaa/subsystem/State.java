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

    public static State fromCode(int code) {
        for (State state : State.values()) {
            if (state.getCode() == code) {
                return state;
            }
        }
        throw new IllegalArgumentException("No enum constant with code " + code);
    }
}
