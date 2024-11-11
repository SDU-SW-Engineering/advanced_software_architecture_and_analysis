import asyncio
import os
import sys
import time

from messaging import send_message, get_message_queue_connection
from processing import start_processing, stop_processing, go_thorough

async def turn_on() -> None:
    send_message("Turning on the device")
    await start_processing()

async def turn_off() -> None:
    send_message("Turning off the device")
    await stop_processing()

async def main() -> None:
    connection = get_message_queue_connection()
    channel = connection.channel()
    channel.queue_declare(queue='peeling_machine')

    # >>> REMOVE
    # TODO messaging, the following two lines are only for testing
    channel.basic_publish(exchange='', routing_key='peeling_machine', body="Message number one")
    time.sleep(2)
    channel.basic_publish(exchange='', routing_key='peeling_machine', body="Message number two")
    # REMOVE <<<

    task = asyncio.create_task(start_processing())
    await asyncio.sleep(5)
    await go_thorough()
    await asyncio.sleep(5)
    await stop_processing()
    await task
    connection.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
