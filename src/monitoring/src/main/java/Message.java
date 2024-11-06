import java.time.Instant;

public class Message {
    private long id;
    private String message;
    private long subsystemID;
    private Instant timestamp;

    public Message(String message, long subsystemID) {
        this.id = 0; // We will probably generate this with the database right?
        this.message = message;
        this.subsystemID = subsystemID;
        this.timestamp = Instant.now();
    }

    public static void handleMessage(String message) {
        Message currMessage = new Message(message, 0);
        System.out.println(currMessage);
        storeMessageToDatabase(currMessage);
    }

    private static void storeMessageToDatabase(Message message) {
        // This is probably for you LARA
    }

    @Override
    public String toString() {
        return "Message{" +
                "id=" + id +
                ", message='" + message + '\'' +
                ", subsystemID=" + subsystemID +
                ", timestamp=" + timestamp +
                '}';
}
}
