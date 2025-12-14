# Build stage
FROM eclipse-temurin:21 AS builder

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

# Runtime stage
FROM eclipse-temurin:21-jre

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 10003 appuser

# Copy the built JAR from builder stage
COPY --from=builder /app/target/sortingsubsystem.jar .

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run the application
CMD ["java", "-jar", "sortingsubsystem.jar"]