package dk.sdu.odense.tek.asaa;

import org.postgresql.ds.PGSimpleDataSource;

public class DataBaseConnection {
	private static final String url = "jdbc:postgresql://localhost:5432/monitoring?user=postgres&password=lara";
	private static PGSimpleDataSource dataSource;

	public static PGSimpleDataSource getDataSource() {
		if (dataSource == null) {
			createDataSource();
		}

		return dataSource;
	}

	private static void createDataSource() {
		dataSource = new PGSimpleDataSource();
		dataSource.setUrl(url);
	}
}
