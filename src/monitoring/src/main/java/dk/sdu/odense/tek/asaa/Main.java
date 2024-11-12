package dk.sdu.odense.tek.asaa;

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import dk.sdu.odense.tek.asaa.subsystem.SubsystemType;
import dk.sdu.odense.tek.asaa.subsystem.Subsystem;

/**
 * Main class for the monitoring module. Entrypoint of the application.
 */
public class Main {
    private Main() {
        throw new AssertionError("This class is not intended for instantiation.");
    }

    public static void main(String[] args) throws IOException, TimeoutException {
        // todo: Subsystem peeler should have updated state based on the message
        // received
        Subsystem peeler = new Subsystem(SubsystemType.PEELER);
        MessageHandler.listenToMessages();
    }
}
