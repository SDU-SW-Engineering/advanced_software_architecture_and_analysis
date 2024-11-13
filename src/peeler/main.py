import asyncio
import os
import sys

from messaging import establish_message_queue
from processing import start_processing, stop_processing, go_thorough
from states import State
from src.peeler.messaging import send_message_with_code, close_connection


async def turn_on() -> None:
    send_message_with_code("Turning on the device", State.TURNED_ON)
    await start_processing()

async def turn_off() -> None:
    send_message_with_code("Turning off the device", State.TURNED_OFF)
    await stop_processing()

async def main() -> None:
    establish_message_queue()

    task = asyncio.create_task(start_processing())
    await asyncio.sleep(5)
    await go_thorough()
    await asyncio.sleep(5)
    await stop_processing()
    await task
    close_connection()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
