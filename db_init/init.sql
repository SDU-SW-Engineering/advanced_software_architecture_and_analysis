CREATE TABLE IF NOT EXISTS message_log (
    id SERIAL PRIMARY KEY,
    messageBody VARCHAR(255) NOT NULL,
    systemId VARCHAR(50) NOT NULL,
    messageSent VARCHAR(255) NOT NULL
    messageReceived VARCHAR(255) NOT NULL
);
