package com.pasta.dbinterface.db;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.*;

public class DatabaseManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(DatabaseManager.class);

    private final String dbUrl;
    private Connection connection;

    public DatabaseManager(String dbUrl) {
        this.dbUrl = dbUrl;
        this.connection = connectWithRetry();
    }

    private Connection connectWithRetry() {
        int maxRetries = 30;
        int retryCount = 0;

        while (retryCount < maxRetries) {
            try {
                Connection conn = DriverManager.getConnection(dbUrl);
                LOGGER.info("Connected to database successfully");
                return conn;
            } catch (SQLException e) {
                retryCount++;
                LOGGER.warn("Failed to connect to database (attempt " + retryCount + "/" + maxRetries + "): " + e.getMessage());
                if (retryCount < maxRetries) {
                    try {
                        Thread.sleep(5000);  // Wait 5 seconds before retrying
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                }
            }
        }

        LOGGER.error("Failed to connect to database after " + maxRetries + " attempts");
        throw new RuntimeException("Could not connect to database");
    }

    public long getTotalStockByBladeTypeAndFreshness(String bladeType, boolean isFresh) {
        String query = "SELECT SUM(inStock) FROM pasta_db.batches WHERE blade_type = ? AND isFresh = ?";

        try (PreparedStatement stmt = connection.prepareStatement(query)) {
            stmt.setString(1, bladeType);
            stmt.setBoolean(2, isFresh);

            ResultSet rs = stmt.executeQuery();
            if (rs.next()) {
                Object result = rs.getObject(1);
                return result != null ? ((Number) result).longValue() : 0L;
            }
        } catch (SQLException e) {
            LOGGER.error("Error querying total stock: " + e.getMessage());
            // Attempt to reconnect on error
            try {
                connection = connectWithRetry();
            } catch (Exception reconnectError) {
                LOGGER.error("Failed to reconnect: " + reconnectError.getMessage());
            }
        }

        return 0L;
    }

    public void close() {
        if (connection != null) {
            try {
                connection.close();
                LOGGER.info("Database connection closed");
            } catch (SQLException e) {
                LOGGER.error("Error closing database connection: " + e.getMessage());
            }
        }
    }
}