import random
import asyncio

from messaging import send_message_with_code
from states import State
from weighing import weigh_apple, weigh_fast_peel, weigh_thorough_peel, weigh_orange, weigh_fast_zest, weigh_thorough_zest
from cleaning import clean

__processing_event__ = asyncio.Event()
__peeling_mode_queue__ = asyncio.Queue()

async def start_processing() -> None:
    print("Starting processing")
    global __processing_event__
    __processing_event__.set()
    await __peeling_mode_queue__.put("thorough")
    asyncio.create_task(clean_every_thirty_seconds())
    while __processing_event__.is_set():
        await process_cycle()

async def stop_processing() -> None:
    print("Stopping processing")
    global __processing_event__
    if __processing_event__.is_set():
        __processing_event__.cancel()
        try:
            await __processing_event__
        except asyncio.CancelledError:
            pass
        __processing_event__ = None

"""
This function copuld stop the processing loop immediately without letting it finish the current cycle
def emergency_stop() -> None:
    print("Emergency stop")
    processing_event.clear()
"""

async def process_cycle() -> None:
    global __peeling_mode_queue__
    if random.random() < 0.005:
        await idle()
    else:
        is_apple = random.choice([True, False])
        peeling_mode = await __peeling_mode_queue__.get()
        __peeling_mode_queue__.put_nowait(peeling_mode)
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
    global __peeling_mode_queue__
    await __peeling_mode_queue__.put("fast")
    print("Switched to fast peeling mode")

async def go_thorough() -> None:
    global __peeling_mode_queue__
    await __peeling_mode_queue__.put("thorough")
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
    global __processing_event__
    while __processing_event__.is_set():
        await asyncio.sleep(30)
        await clean()

async def idle() -> None:
    send_message_with_code("The device is idle", State.IDLE)
    time = random.randint(1, 5)
    await asyncio.sleep(time)
    send_message_with_code("The device is running", State.RUNNING)
    print(f"This device was idle for {time} seconds")
    