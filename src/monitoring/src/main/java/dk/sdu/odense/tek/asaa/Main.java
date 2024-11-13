package dk.sdu.odense.tek.asaa;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeoutException;

import dk.sdu.odense.tek.asaa.subsystem.SubsystemType;
import dk.sdu.odense.tek.asaa.subsystem.Subsystems;
import dk.sdu.odense.tek.asaa.subsystem.Subsystem;

/**
 * Main class for the monitoring module. Entrypoint of the application.
 */
public class Main {
    private Main() {
        throw new AssertionError("This class is not intended for instantiation.");
    }

    public static void main(String[] args) throws IOException, TimeoutException {

        List<Subsystem> currentSubsystems = Arrays.asList(
                new Subsystem(SubsystemType.PEELER),
                new Subsystem(SubsystemType.CONVEYBELT),
                new Subsystem(SubsystemType.SQUEEZER));

        Subsystems.addSubsystems(currentSubsystems);

        MessageHandler.listenToMessages();
    }
}
