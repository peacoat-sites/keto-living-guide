#!/usr/bin/env python3
"""Fetch keto-relevant food macros from USDA FoodData Central -> data/keto_foods.json.
Net carbs = total carbohydrate - fiber, per 100g. Prefers SR Legacy / Foundation data.
Runs in GitHub Actions on a schedule; DEMO_KEY works for this low volume.
"""
import urllib.request, urllib.parse, json, time, os, sys

API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
BASE = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Curated keto-relevant foods: (display name, category, search query)
FOODS = [
    ("Avocado", "Fruit", "avocado raw"),
    ("Egg, whole", "Protein", "egg whole raw fresh"),
    ("Chicken breast", "Protein", "chicken breast meat only raw"),
    ("Salmon, Atlantic", "Protein", "salmon atlantic wild raw"),
    ("Ground beef (80/20)", "Protein", "ground beef 80 20 raw"),
    ("Bacon", "Protein", "pork bacon raw"),
    ("Cheddar cheese", "Dairy", "cheese cheddar"),
    ("Cream cheese", "Dairy", "cream cheese"),
    ("Butter", "Fat", "butter without salt"),
    ("Almonds", "Nuts", "almonds raw"),
    ("Walnuts", "Nuts", "walnuts english"),
    ("Macadamia nuts", "Nuts", "macadamia nuts raw"),
    ("Spinach", "Vegetable", "spinach raw"),
    ("Broccoli", "Vegetable", "broccoli raw"),
    ("Cauliflower", "Vegetable", "cauliflower raw"),
    ("Zucchini", "Vegetable", "squash zucchini raw"),
    ("Asparagus", "Vegetable", "asparagus raw"),
    ("Olive oil", "Fat", "oil olive"),
    ("Coconut oil", "Fat", "oil coconut"),
    ("Greek yogurt, plain whole", "Dairy", "yogurt greek plain whole milk"),
    ("Heavy cream", "Dairy", "cream heavy whipping"),
    ("Pork chop", "Protein", "pork loin chop raw"),
    ("Shrimp", "Protein", "shrimp raw"),
    ("Tuna", "Protein", "fish tuna fresh raw"),
    ("Cabbage", "Vegetable", "cabbage raw"),
    ("Kale", "Vegetable", "kale raw"),
    ("Mushrooms, white", "Vegetable", "mushrooms white raw"),
    ("Bell pepper, green", "Vegetable", "peppers sweet green raw"),
    ("Cucumber", "Vegetable", "cucumber with peel raw"),
    ("Blackberries", "Fruit", "blackberries raw"),
]

NUT = {
    "Energy": None, "Protein": None, "Total lipid (fat)": None,
    "Carbohydrate, by difference": None, "Fiber, total dietary": None,
}

def get_nutrients(food):
    params = urllib.parse.urlencode({
        "query": food, "pageSize": 5, "api_key": API_KEY,
        "dataType": "Foundation,SR Legacy",
    })
    req = urllib.request.Request(f"{BASE}?{params}", headers={"User-Agent": "keto-data/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    foods = data.get("foods", [])
    if not foods:
        return None
    f = foods[0]
    vals = {k: None for k in NUT}
    for n in f.get("foodNutrients", []):
        name = n.get("nutrientName", "")
        if name in vals:
            # Energy can appear as kcal and kJ; take kcal
            if name == "Energy" and n.get("unitName", "").upper() != "KCAL":
                continue
            vals[name] = n.get("value")
    return vals

out = []
for display, cat, query in FOODS:
    try:
        v = get_nutrients(query)
        if not v or v["Carbohydrate, by difference"] is None:
            print(f"  skip {display}: no data", file=sys.stderr); continue
        carb = v["Carbohydrate, by difference"] or 0
        fiber = v["Fiber, total dietary"] or 0
        net = round(max(0, carb - fiber), 1)
        out.append({
            "name": display, "category": cat,
            "net_carbs": net,
            "total_carbs": round(carb, 1),
            "fiber": round(fiber, 1),
            "protein": round(v["Protein"] or 0, 1),
            "fat": round(v["Total lipid (fat)"] or 0, 1),
            "calories": round(v["Energy"] or 0),
        })
        print(f"  {display}: net {net}g carb, {round(v['Protein'] or 0,1)}g protein, {round(v['Total lipid (fat)'] or 0,1)}g fat")
        time.sleep(0.6)
    except Exception as e:
        print(f"  ERROR {display}: {e}", file=sys.stderr)

out.sort(key=lambda x: x["net_carbs"])
result = {
    "source": "USDA FoodData Central (fdc.nal.usda.gov)",
    "basis": "per 100g, raw",
    "note": "Net carbs = total carbohydrate minus dietary fiber.",
    "foods": out,
}
dest = sys.argv[1] if len(sys.argv) > 1 else "keto_foods.json"
with open(dest, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2)
print(f"\nWrote {len(out)} foods to {dest}")
