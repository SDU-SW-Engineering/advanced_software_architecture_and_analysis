import random
import asyncio

async def clean() -> None:
    time = random.randint(1, 5)
    await asyncio.sleep(time)
    print(f"Cleaning the device for {time} seconds")
    pass
