import random
import asyncio

from messaging import send_message_with_code
from states import State
from weighing import weigh_apple, weigh_fast_peel, weigh_thorough_peel, weigh_orange, weigh_fast_zest, weigh_thorough_zest
from cleaning import clean

processing_event = asyncio.Event()
peeling_mode_queue = asyncio.Queue()

async def start_processing() -> None:
    print("Starting processing")
    processing_event.set()
    await peeling_mode_queue.put("thorough")
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
        peeling_mode = await peeling_mode_queue.get()
        peeling_mode_queue.put_nowait(peeling_mode)
        if is_apple:
            if peeling_mode == "fast":
                await fast_peel()
            else:
                await thorough_peel()
        else:
            if peeling_mode == "fast":
                await fast_zest()
            else:
                await thorough_zest()

async def go_fast() -> None:
    await peeling_mode_queue.put("fast")
    print("Switched to fast peeling mode")

async def go_thorough() -> None:
    await peeling_mode_queue.put("thorough")
    print("Switched to thorough peeling mode")

async def fast_peel() -> None:
    await asyncio.sleep(1)
    weigh_apple()
    weigh_fast_peel()
    print("Peeling an apple")

async def thorough_peel() -> None:
    await asyncio.sleep(1.5)
    weigh_apple()
    weigh_thorough_peel()
    print("Peeling an apple")

async def fast_zest() -> None:
    await asyncio.sleep(2)
    weigh_orange()
    weigh_fast_zest()
    print("Zesting an orange")

async def thorough_zest() -> None:
    await asyncio.sleep(2.7)
    weigh_orange()
    weigh_thorough_zest()
    print("Zesting an orange")

async def clean_every_thirty_seconds() -> None:
    while processing_event.is_set():
        await asyncio.sleep(4)
        await clean()

async def idle() -> None:
    send_message_with_code("The device is idle", State.IDLE)
    time = random.randint(1, 5)
    await asyncio.sleep(time)
    print(f"This device was idle for {time} seconds")
    