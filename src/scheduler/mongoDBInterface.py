import pymongo

# Connect to MongoDB
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["mydatabase"]
mycol = mydb["recipes"]


def insertRecipe(orderID, chassisID, engineID, interiorID, paintID):
    recipe = {
        "_id": orderID, # OrderID is Primary key
        "ChassisID": chassisID,
        "EngineID": engineID,
        "InteriorID": interiorID,
        "PaintID": paintID,
        "Steps": [
            {"step": 1, "task": f"Assemble chassis {chassisID}"},
            {"step": 2, "task": f"Install engine {engineID}"},
            {"step": 3, "task": f"Install interior {interiorID}"},
            {"step": 4, "task": f"Apply paint {paintID}"}
        ],
       
        
    }

    result = mycol.insert_one(recipe)
    print(f"Recipe inserted successfully for OrderID {orderID} (RecipeID: {result.inserted_id})")



def fetchRecipe(orderID):
    recipe = mycol.find_one({"OrderID": orderID})
    if recipe:
        print("Recipe found:")
        print(recipe)
    else:
        print("No recipe found for OrderID:", orderID)
    return recipe
