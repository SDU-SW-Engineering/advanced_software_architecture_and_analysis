import javax.sql.DataSource; 
import org.postgresql.ds.PGSimpleDataSource;

public class DataBaseConnection {

	 public static DataSource createDataSource() {
			// The url specifies the address of our database along with username and password credentials
			// you should replace these with your own username and password
			
		 	// part which we will have to change depending on your pgadmin app 
		 	final String url =
			         "jdbc:postgresql://localhost:5432/monitoring?user=postgres&password=lara";
			
			 final PGSimpleDataSource dataSource = new PGSimpleDataSource();
			 dataSource.setUrl(url);
			 return dataSource;
		 
	}

}
