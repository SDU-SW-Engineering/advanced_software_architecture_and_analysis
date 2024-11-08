import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException; 
import javax.sql.DataSource; 

public class Message {
    private long id;
    private String message;
    private long subsystemID;
    private Instant timestamp;
    
    static DataSource datasource =  DataBaseConnection.createDataSource(); 
    //Connection connection = datasource.getConnection(); 
    
    public static Connection getConnection() throws SQLException {
		return datasource.getConnection(); 
	}
    
    public Message(String message, long subsystemID) {
        //this.id = 0; // We will probably generate this with the database right?
        this.message = message;
        this.subsystemID = subsystemID;
        this.timestamp = Instant.now();
    }

    public static void handleMessage(String message) {
        Message currMessage = new Message(message, 0);
        //System.out.println(currMessage);
        storeMessageToDatabase(currMessage);
    }

    private static void storeMessageToDatabase(Message message) {
        // This is probably for you LARA
    	Connection conn;
		try {
			conn = datasource.getConnection();
			PreparedStatement insertStmt =
	                conn.prepareStatement("INSERT INTO message_log( message, systemid, timestamp) VALUES ( ?, ?, ?)");
			//setLong(1, getLastId());
	        insertStmt.setString(1, message.message);
	        insertStmt.setLong(2, message.subsystemID);
	        
	        LocalDateTime datetime = LocalDateTime.ofInstant(message.timestamp, ZoneOffset.UTC);
	        String formatted = DateTimeFormatter.ofPattern("yyyy-MM-dd hh:mm:ss").format(datetime);
	        
	        insertStmt.setString(3, formatted);
	        System.out.println(message.message + ", "+ message.subsystemID + ", "+ formatted); 
	        int insertedRows = insertStmt.executeUpdate();
	        
		} catch (SQLException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} 
    	
    }
    
    public static Long getLastId() {
    	
    	String sql = "SELECT id FROM message_log ORDER BY id DESC LIMIT 1";
    	
    	try (Connection conn = datasource.getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql);
                ResultSet rs = pstmt.executeQuery()) {

               if (rs.next()) {
            	   
                   Long lastId = rs.getLong("id");
                   Long retVal = lastId +1; 
                   System.out.println("Last ID: " + lastId);
                   
                   return retVal; 
               } else {
                   System.out.println("No records found in the table.");
               }

           } catch (Exception e) {
               e.printStackTrace();
           }
    	return null; 
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
