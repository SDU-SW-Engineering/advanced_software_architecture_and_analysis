import random

def weigh_apple() -> None:
    weight = random.uniform(150, 300)
    print(f"Weighing an apple: {weight:.2f} grams")
    return

def weigh_fast_peel() -> None:
    weight = random.uniform(10, 35)
    print(f"Weighing a peel: {weight:.2f} grams")
    return

def weigh_thorough_peel() -> None:
    weight = random.uniform(20, 50)
    print(f"Weighing a peel: {weight:.2f} grams")
    return

def weigh_orange() -> None:
    weight = random.uniform(200, 400)
    print(f"Weighing an orange: {weight:.2f} grams")
    return

def weigh_fast_zest() -> None:
    weight = random.uniform(5, 15)
    print(f"Weighing a zest: {weight:.2f} grams")
    return

def weigh_thorough_zest() -> None:
    weight = random.uniform(10, 25)
    print(f"Weighing a zest: {weight:.2f} grams")
    return