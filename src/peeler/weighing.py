import random
from pymongo.mongo_client import MongoClient

cluster = MongoClient("mongodb+srv://admin:admin123@cluster0.k0olb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db= cluster["peeling_system"]
collection= db["peeling"]

def weigh_apple() :
    weight = random.uniform(150, 300)
    return weight

def weigh_fast_peel() -> None:
    weight = random.uniform(10, 35)
    apple_weight = weigh_apple()
    print(f"Weighing a peel: {weight:.2f} grams, Weighing an apple: {apple_weight()} grams")
    resource = {"name": "apple", "weight": apple_weight, "waste_weight": weight}
    collection.insert_one(resource)
    return

def weigh_thorough_peel() -> None:
    weight = random.uniform(20, 50)
    apple_weight = weigh_apple()
    print(f"Weighing a peel: {weight:.2f} grams, Weighing an apple: {apple_weight} grams")
    resource = {"name": "apple", "weight": apple_weight, "waste_weight": weight}
    collection.insert_one(resource)
    return

def weigh_orange():
    weight = random.uniform(200, 400)
    return weight

def weigh_fast_zest() -> None:
    weight = random.uniform(5, 15)
    orange_weight = weigh_orange()
    print(f"Weighing a zest: {weight:.2f} grams, weighing an apple: {orange_weight} grams")
    resource = {"name": "orange", "weight": orange_weight, "waste_weight": weight}
    collection.insert_one(resource)
    return

def weigh_thorough_zest() -> None:
    weight = random.uniform(10, 25)
    orange_weight = weigh_orange()
    print(f"Weighing a zest: {weight:.2f} grams, weighing an apple: {orange_weight} grams")
    resource = {"name": "orange", "weight": orange_weight, "waste_weight": weight}
    collection.insert_one(resource)
    return
    