package dk.sdu.odense.tek.asaa.subsystem;

public class Subsystem {
    private final long id;
    private SubsystemType type;
    private State currentState;

    public Subsystem(SubsystemType type) {
        this.id = 1;
        this.type = type;
        this.currentState = State.UNKNOWN;
    }

    public void setCurrentState(State state) {
        this.currentState = state;
    }
}
