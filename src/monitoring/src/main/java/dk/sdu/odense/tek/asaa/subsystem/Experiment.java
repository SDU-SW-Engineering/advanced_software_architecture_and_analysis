package dk.sdu.odense.tek.asaa.subsystem;

import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.Duration;

import dk.sdu.odense.tek.asaa.Message;

public abstract class Experiment {
    private static final String CSV_FILE_PATH = "/usr/app/experiment_results.csv";
    private static Boolean fileCreated = false;

    public static void createCSVFile() {
        try (FileWriter writer = new FileWriter(CSV_FILE_PATH)) {
            writer.append("MessageBody,SentTimestamp,ReceivedTimestamp,TimeDifference\n");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static void writeToCSV(Message message) {
        if (!fileCreated) {
            createCSVFile();
            fileCreated = true;
        }
        try (FileWriter writer = new FileWriter(CSV_FILE_PATH, true)) {
            Duration timeDifference = Duration.between(message.getSentTimestamp(), message.getReceivedTimestamp());
            writer.append(message.getMessageBody())
                  .append(',')
                  .append(message.getSentTimestamp().toString())
                  .append(',')
                  .append(message.getReceivedTimestamp().toString())
                  .append(',')
                  .append(String.valueOf(timeDifference.toMillis()))
                  .append('\n');
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
