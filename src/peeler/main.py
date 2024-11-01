import asyncio
from src.peeler.messaging import send_message
from src.peeler.processing import start_processing, stop_processing
import random

async def turn_on() -> None:
    send_message("Turning on the device")
    await start_processing()

async def turn_off() -> None:
    send_message("Turning off the device")
    await stop_processing()

async def main() -> None:
    task = asyncio.create_task(start_processing())
    await asyncio.sleep(10)
    await stop_processing()
    await task

if __name__ == "__main__":
    asyncio.run(main())