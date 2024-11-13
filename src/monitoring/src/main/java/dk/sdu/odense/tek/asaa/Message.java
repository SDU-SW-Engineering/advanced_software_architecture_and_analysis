package dk.sdu.odense.tek.asaa;

import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import dk.sdu.odense.tek.asaa.subsystem.State;
import dk.sdu.odense.tek.asaa.subsystem.Subsystems;

public class Message {
    private long id;
    private String message;
    private long subsystemID;
    private Instant sendOutTimestamp;
    private Instant timestamp;

    private Message(String message) {
        // todo: assign ID and subsystemID
        String[] parsedMessage = message.split(";");
        this.message = parsedMessage[0];
        this.subsystemID = Long.parseLong(parsedMessage[1]);
        Subsystems.getSubsystem(subsystemID).setCurrentState(State.valueOf(parsedMessage[2]));
        this.sendOutTimestamp = Instant.parse(parsedMessage[3]);
        this.timestamp = Instant.now();
    }

    public static void handleMessage(String messageString) {
        Message message = new Message(messageString);
        storeMessageToDatabase(message);
    }

    public String getMessage() {
        return message;
    }

    public long getSubsystemID() {
        return subsystemID;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    @Override
    public String toString() {
        return "Message{" +
                "id=" + id +
                ", message='" + message + '\'' +
                ", subsystemID=" + subsystemID +
                ", sendOutTimestamp=" + sendOutTimestamp +
                ", timestamp=" + timestamp +
                '}';
    }

    private static void storeMessageToDatabase(Message message) {
        try {
            PreparedStatement statement = DataBaseConnection.getDataSource().getConnection()
                    .prepareStatement("INSERT INTO message_log( message, systemid, timestamp) VALUES ( ?, ?, ?)");

            LocalDateTime datetime = LocalDateTime.ofInstant(message.getTimestamp(), ZoneOffset.UTC);
            String formatted = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss").format(datetime);

            statement.setString(1, message.getMessage());
            statement.setLong(2, message.getSubsystemID());
            statement.setString(3, formatted);

            int insertedRows = statement.executeUpdate();

        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
}
