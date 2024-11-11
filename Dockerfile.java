FROM maven:3.6.3-jdk-11 AS build  
COPY src/monitoring/src /usr/src/app/src
COPY src/monitoring/pom.xml /usr/src/app
RUN mvn -f /usr/src/app/pom.xml -B dependency:go-offline
RUN mvn -f /usr/src/app/pom.xml clean package

FROM gcr.io/distroless/java  
COPY --from=build /usr/src/app/target/monitoring.jar /usr/app/monitoring.jar  
EXPOSE 8080  
ENTRYPOINT ["java","-jar","/usr/app/monitoring.jar"] 
