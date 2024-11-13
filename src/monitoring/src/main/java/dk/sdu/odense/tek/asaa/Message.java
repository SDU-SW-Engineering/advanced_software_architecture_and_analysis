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
    private Instant messageSentTimestamp;
    private Instant messageReceivedTimestamp;

    private Message(String message) {
        String[] parsedMessage = message.split(";");

        this.message = parsedMessage[0];
        this.subsystemID = Long.parseLong(parsedMessage[1]);
        this.messageSentTimestamp = Instant.parse(parsedMessage[3]);
        this.messageReceivedTimestamp = Instant.now();

        Subsystems.getSubsystem(subsystemID).setCurrentState(State.valueOf(parsedMessage[2]));
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

    public Instant getMessageReceivedTimestamp() {
        return messageReceivedTimestamp;
    }

    public Instant getMessageSentTimestamp() {
        return messageSentTimestamp;
    }

    @Override
    public String toString() {
        return "Message{" +
                "id=" + id +
                ", message='" + message + '\'' +
                ", subsystemID=" + subsystemID +
                ", sendTimestamp=" + messageSentTimestamp +
                ", messageReceivedTimestamp=" + messageReceivedTimestamp +
                '}';
    }

    private static void storeMessageToDatabase(Message message) {
        try {
            PreparedStatement statement = DataBaseConnection.getDataSource().getConnection()
                    .prepareStatement(
                            "INSERT INTO message_log( message, systemid, messageReceivedTimestamp) VALUES ( ?, ?, ?)");

            LocalDateTime datetimeSent = LocalDateTime.ofInstant(message.getMessageSentTimestamp(), ZoneOffset.UTC);
            String datetimeSentString = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss.SSS").format(datetimeSent);

            LocalDateTime datetimeReceived = LocalDateTime.ofInstant(message.getMessageReceivedTimestamp(),
                    ZoneOffset.UTC);
            String datetimeReceivedString = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss.SSS")
                    .format(datetimeReceived);

            statement.setString(1, message.getMessage());
            statement.setLong(2, message.getSubsystemID());
            statement.setString(3, datetimeSentString);
            statement.setString(4, datetimeReceivedString);

            int insertedRows = statement.executeUpdate();

        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
}
