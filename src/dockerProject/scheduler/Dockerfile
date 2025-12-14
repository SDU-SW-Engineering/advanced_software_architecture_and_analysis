# Use eclipse-temurin which is always available
FROM eclipse-temurin:21

WORKDIR /app

# Install Maven
RUN apt-get update && apt-get install -y --no-install-recommends \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Copy pom.xml
COPY pom.xml .

# Copy source code
COPY src ./src

# Build the application
RUN mvn clean package -DskipTests

# Create non-root user for security (use UID 10001 instead)
RUN useradd -m -u 10001 appuser

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run the application
CMD ["java", "-jar", "target/scheduler.jar"]