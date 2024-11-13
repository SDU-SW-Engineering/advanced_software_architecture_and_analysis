package dk.sdu.odense.tek.asaa.subsystem;

public class Subsystem {
    private final long id;
    private SubsystemType type;
    private State currentState;
    private static long idCounter = 0;

    public Subsystem(SubsystemType type) {
        this.id = idCounter++;
        this.type = type;
        this.currentState = State.UNKNOWN;
    }

    public long getId() {
        return id;
    }

    public State getCurrentState() {
        return currentState;
    }

    public void setCurrentState(State state) {
        this.currentState = state;
    }

    public SubsystemType getSubsystemType() {
        return type;
    }
}
