public class MessageHandler {
    public static void handleMessage(String message) {
        System.out.println(message);
        storeMessageToDatabase(message);
    }

    private static void storeMessageToDatabase(String message) {
        // This is probably for you LARA
    }
}
