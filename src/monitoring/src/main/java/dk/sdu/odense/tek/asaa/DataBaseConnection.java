package dk.sdu.odense.tek.asaa;

import org.postgresql.ds.PGSimpleDataSource;

public abstract class DataBaseConnection {
	private static final String url = "jdbc:postgresql://postgres:5432/monitoring?user=postgres&password=juicelizzo";
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
