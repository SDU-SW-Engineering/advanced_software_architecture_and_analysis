import pika
import os

def get_message_queue_connection():
    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))

    return connection


def send_message_with_code(channel, message, code) -> None:
    message = f"{message} {code}"
    send_message(channel, message)


def send_message(channel, message) -> None:
    print(f"Sending message: {message}")
    channel.basic_publish(exchange='', routing_key='peeling_machine', body=message)
