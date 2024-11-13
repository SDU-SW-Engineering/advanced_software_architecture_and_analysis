package dk.sdu.odense.tek.asaa.subsystem;

import java.util.HashMap;
import java.util.Map;

public abstract class Subsystems {
    private static Map<Long, Subsystem> subsystems = new HashMap<>();

    public static void addSubsystem(Subsystem subsystem) {
        subsystems.put(subsystem.getId(), subsystem);
    }

    public static Subsystem getSubsystem(long id) {
        return subsystems.get(id);
    }

    public static void updateSubsystemState(long id, State newState) {
        Subsystem subsystem = subsystems.get(id);
        if (subsystem != null) {
            subsystem.setCurrentState(newState);
        } else {
            System.out.println("Subsystem with ID " + id + " not found.");
        }
    }

}
