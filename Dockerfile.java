

# FROM maven:3.6.0-jdk-11-slim AS build
# # Step 2: Set the working directory inside the container
# WORKDIR /app

# # Step 3: Copy the pom.xml and install dependencies (to cache dependencies)
# COPY src/monitoring/ monitoring/
# RUN mvn -f monitoring/pom.xml clean package

# # Step 4: Copy the rest of the project files
# # COPY . .

# # Step 5: Compile and package the application

# # Step 6: Use a smaller JRE image to run the application
# FROM openjdk:11-jre-slim
# COPY --from=build monitoring/target/main-0.0.1-SNAPSHOT.jar /usr/local/lib/main.jar
# ENTRYPOINT ["java", "-jar", "/usr/local/lib/main.jar"]

FROM maven:3.6.3-jdk-11 AS build  
COPY src/monitoring/src /usr/src/app/src
COPY src/monitoring/pom.xml /usr/src/app
RUN mvn -f /usr/src/app/pom.xml -B dependency:go-offline
RUN mvn -f /usr/src/app/pom.xml clean package

FROM gcr.io/distroless/java  
COPY --from=build /usr/src/app/target/monitoring.jar /usr/app/monitoring.jar  
EXPOSE 8080  
ENTRYPOINT ["java","-jar","/usr/app/monitoring.jar"] 


# # Use an official Maven image as the base image
# FROM maven:3.8.4-openjdk-11-slim AS build
# # Set the working directory in the container
# WORKDIR /app
# # Copy the pom.xml and the project files to the container
# COPY src/monitoring/pom.xml .
# COPY src/monitoring/src ./src
# # Build the application using Maven
# RUN mvn clean package -DskipTests
# # Use an official OpenJDK image as the base image
# FROM openjdk:11-jre-slim
# # Set the working directory in the container
# WORKDIR /app
# # Copy the built JAR file from the previous stage to the container
# COPY --from=build /app/target/monitoring.jar .
# # Set the command to run the application
# CMD ["java", "-jar", "monitoring.jar"]
