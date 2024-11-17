package dk.sdu.odense.tek.asaa;

import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import dk.sdu.odense.tek.asaa.subsystem.State;
import dk.sdu.odense.tek.asaa.subsystem.Subsystems;
import dk.sdu.odense.tek.asaa.subsystem.Experiment;

public class Message {
    private long id;
    private String messageBody;
    private long subsystemID;
    private LocalDateTime sentTimestamp;
    private LocalDateTime receivedTimestamp;

    private Message(String message) {
        String[] parsedMessage = message.split(";");

        this.messageBody = parsedMessage[0];
        this.subsystemID = Long.parseLong(parsedMessage[1]);

        DateTimeFormatter inputFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSSSSS");

        this.sentTimestamp = LocalDateTime.parse(parsedMessage[3], inputFormatter);
        this.receivedTimestamp = LocalDateTime.ofInstant(Instant.now(),
                ZoneOffset.UTC);

        
        int stateCode = Integer.parseInt(parsedMessage[2]);
        Subsystems.getSubsystem(subsystemID).setCurrentState(State.fromCode(stateCode));
        System.out.println(Subsystems.getSubsystem(subsystemID).getCurrentState());
        System.out.println(receivedTimestamp.toString() + sentTimestamp.toString());
    }

    public static void handleMessage(String messageString) {
        Message message = new Message(messageString);
        storeMessageToDatabase(message);
        Experiment.writeToCSV(message);
    }

    @Override
    public String toString() {
        return "Message{" +
                "id=" + id +
                ", message='" + messageBody + '\'' +
                ", subsystemID=" + subsystemID +
                ", sendTimestamp=" + sentTimestamp +
                ", messageReceivedTimestamp=" + receivedTimestamp +
                '}';
    }

    private static void storeMessageToDatabase(Message message) {
        try {
            PreparedStatement statement = DataBaseConnection
                    .getDataSource()
                    .getConnection()
                    .prepareStatement(
                            "INSERT INTO message_log( messageBody, systemId, messageSent, messageReceived) VALUES ( ?, ?, ?, ?)");

            String datetimeSentString = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss.SSS").format(message.sentTimestamp);

            String datetimeReceivedString = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss.SSS")
                    .format(message.receivedTimestamp);

            statement.setString(1, message.messageBody);
            statement.setLong(2, message.subsystemID);
            statement.setString(3, datetimeSentString);
            statement.setString(4, datetimeReceivedString);

            int insertedRows = statement.executeUpdate();

        } catch (SQLException e) {
            System.err.print("An exception occurred: ");
            e.printStackTrace();
        }
    }

    public LocalDateTime getSentTimestamp() {
        return sentTimestamp;
    }

    public LocalDateTime getReceivedTimestamp() {
        return receivedTimestamp;
    }

    public String getMessageBody() {
        return messageBody;
    }
}
