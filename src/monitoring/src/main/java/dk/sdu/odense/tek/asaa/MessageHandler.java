package dk.sdu.odense.tek.asaa;

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import com.rabbitmq.client.CancelCallback;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DeliverCallback;

public class MessageHandler {
    private final static String QUEUE_NAME = "peeling_machine";
    private final static Boolean DURABLE_QUEUE = false;

    public static void listenToMessages() throws IOException, TimeoutException {
        String rabbitmqHost = System.getenv("RABBITMQ_HOST");
        int rabbitmqPort = Integer.parseInt(System.getenv("RABBITMQ_PORT"));

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(rabbitmqHost);
        factory.setPort(rabbitmqPort);

        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.queueDeclare(QUEUE_NAME, DURABLE_QUEUE, false, false, null);

        System.out.println("Listening for new messages.");

        channel.basicConsume(QUEUE_NAME, true, deliverCallback, cancelCallback);
    }

    private final static DeliverCallback deliverCallback = (consumerTag, delivery) -> {
        String message = new String(delivery.getBody(), "UTF-8");
        System.out.println("Just Received '" + message + "' message.");
        saveMessageToDatabase(message);
    };

    private final static CancelCallback cancelCallback = (consumerTag) -> {
        System.out.println("Consumer monitoring system for the peeling machine (" + consumerTag + ") stopped.");
    };

    private static void saveMessageToDatabase(String message) {
        // This is probably for you LARA
    }
}
