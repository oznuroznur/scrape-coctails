import json
import re

counter = 0

UNIT_MAP = {
    "ml": "ML",
    "cl": "CL",
    "oz": "OZ",
    "dash": "DASH",
    "drop": "DROP",
    "tsp": "TSP",
    "tbsp": "TBSP",
    "bar spoon": "TSP",
    "splash": "SPLASH",
    "slice": "SLICE"
}

def normalize_name(name):
    return name.lower().replace(" ", "_")

def parse_ingredient(text):

    text = text.lower()

    match = re.match(r'(\d+)\s*(ml|cl|oz|dash|drop|tsp|tbsp)\s+(.*)', text)

    if match:
        amount = int(match.group(1))
        unit = UNIT_MAP.get(match.group(2), "PIECE")
        name = match.group(3)

    elif "bar spoon" in text:
        amount = 1
        unit = "TSP"
        name = text.replace("bar spoon", "").strip()

    elif "splash" in text:
        amount = 1
        unit = "SPLASH"
        name = text.replace("a splash of", "").strip()

    else:
        amount = 1
        unit = "PIECE"
        name = text

    name = name.replace("fresh ", "")
    name = name.replace("optional ", "")

    return {
        "name": normalize_name(name),
        "displayName": name.title(),
        "amount": amount,
        "unit": unit
    }


with open("cocktails.json", encoding="utf-8") as f:
    data = json.load(f)

normalized = []

for c in data:

    ingredients = []

    for ing in c["ingredients"]:
        ingredients.append(parse_ingredient(ing))

    cocktail = {
        "name": c["name"],
        "ingredients": ingredients,
        "instructions": [
            {
                "step": 1,
                "text": c["method"]
            }
        ],
        "garnish": c["garnish"]
    }

    normalized.append(cocktail)
    
    counter += 1
    
with open("cocktails_clean.json", "w", encoding="utf-8") as f:
    json.dump(normalized, f, indent=2, ensure_ascii=False)

print("done")
print(f"\nTotal cocktails processed: {counter}")