import random
import asyncio

from src.peeler.messaging import send_message
from src.peeler.weighing import weigh_apple, weigh_peel, weigh_orange, weigh_zest
from src.peeler.cleaning import clean

processing_event = asyncio.Event()

async def start_processing() -> None:
    print("Starting processing")
    processing_event.set()
    asyncio.create_task(clean_every_thirty_seconds())
    while processing_event.is_set():
        await process_cycle()

async def stop_processing() -> None:
    print("Stopping processing")
    processing_event.clear()

"""
This function copuld stop the processing loop immediately without letting it finish the current cycle
def emergency_stop() -> None:
    print("Emergency stop")
    processing_event.clear()
"""

async def process_cycle() -> None:
    if random.random() < 0.005:
        await idle()
    else:
        is_apple = random.choice([True, False])
        if is_apple:
            await peel()
        else:
            await zest()
    return

async def peel() -> None:
    await asyncio.sleep(1)
    weigh_apple()
    weigh_peel()
    print("Peeling an apple")

async def zest() -> None:
    await asyncio.sleep(2)
    weigh_orange()
    weigh_zest()
    print("Zesting an orange")

async def clean_every_thirty_seconds() -> None:
    while processing_event.is_set():
        await asyncio.sleep(4)
        await clean()

async def idle() -> None:
    send_message("The device is idle")
    time = random.randint(1, 5)
    await asyncio.sleep(time)
    print(f"This device was idle for {time} seconds")