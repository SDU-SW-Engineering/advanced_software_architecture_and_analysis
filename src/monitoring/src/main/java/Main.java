import subsystem.Subsystem;
import subsystem.SubsystemType;

/**
 * Main class for the monitoring module. Entrypoint of the application.
 */
public class Main {
    private Main() {
        throw new AssertionError("This class is not intended for instantiation.");
    }

    public static void main(String[] args) {
        Subsystem peeler = new Subsystem(SubsystemType.PEELER);

        MessageHandler.handleMessage("New message from Jakub");
    }
}
