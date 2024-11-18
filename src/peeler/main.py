import asyncio
import os
import sys

from processing import start_processing, stop_processing, go_thorough, go_fast
from states import State
from messaging import send_message_with_code, close_connection


async def turn_on() -> None:
    send_message_with_code("Turning on the device", State.RUNNING)
    await start_processing()

async def turn_off() -> None:
    send_message_with_code("Turning off the device", State.OFF)
    await stop_processing()

async def main() -> None:
    task = asyncio.create_task(turn_on())
    await asyncio.sleep(120)
    await go_thorough()
    await asyncio.sleep(120)
    await go_fast()
    await asyncio.sleep(60)
    await turn_off()
    
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
