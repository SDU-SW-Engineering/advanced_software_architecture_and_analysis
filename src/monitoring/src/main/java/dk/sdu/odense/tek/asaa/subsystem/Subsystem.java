package dk.sdu.odense.tek.asaa.subsystem;

public class Subsystem {
    private final long id;
    private SubsystemType type;
    private State currentState;
    private static long idCounter = 0;

    public Subsystem(long id, SubsystemType type) {
        this.id = id;
        this.type = type;
        this.currentState = State.UNKNOWN;
        idCounter++;
        Subsystems.addSubsystem(this);
    }


    public long getId() {
        return id;
    }

    public void setCurrentState(State state) {
        this.currentState = state;
    }
}
