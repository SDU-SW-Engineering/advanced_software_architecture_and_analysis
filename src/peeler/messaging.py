from datetime import datetime

import pika
import os

__message_queue__ = None

def establish_message_queue():
    global __message_queue__
    if __message_queue__ is not None:
        return None

    rabbitmq_host = os.getenv('RABBITMQ_HOST', 'rabbitmq')
    rabbitmq_port = int(os.getenv('RABBITMQ_PORT', '5672'))

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))

    channel = connection.channel()
    channel.queue_declare(queue='peeling_machine')

    __message_queue__ = channel

    return connection

def close_connection():
    global __message_queue__
    if hasattr(__message_queue__, 'close'):
        __message_queue__.close()
        __message_queue__ = None

def send_message_with_code(message, code) -> None:
    message = f"{message};1;{code.value};{datetime.now()}"
    send_message(message)


def send_message(message) -> None:
    print(f"Sending message: {message}")
    if hasattr(__message_queue__, 'basic_publish'):
        __message_queue__.basic_publish(exchange='', routing_key='peeling_machine', body=message)
    else: raise Exception("Message queue not established")