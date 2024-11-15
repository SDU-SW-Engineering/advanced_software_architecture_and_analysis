package dk.sdu.odense.tek.asaa.subsystem;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public abstract class Subsystems {
    private static Map<Long, Subsystem> subsystems = new HashMap<>();

    public static void addSubsystems(List<Subsystem> subsystemsIterable) {
        subsystemsIterable
                .stream()
                .forEach(Subsystems::addSubsystem);
    }

    public static void addSubsystem(Subsystem subsystem) {
        subsystems.put(subsystem.getId(), subsystem);
    }

    public static Subsystem getSubsystem(long id) {
        System.out.println(subsystems);
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
