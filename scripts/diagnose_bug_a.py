import json

# Load ships data
with open('data/ships_data.json', 'r') as f:
    data = json.load(f)

# Check S5 and S6 coordinates and labels at frames 9, 10, 11
print("=== BUG A DIAGNOSIS ===\n")
print("S5 and S6 data at timestamps 9, 10, 11:\n")

for ship_id in ['S5', 'S6']:
    print(f"{ship_id}:")
    for entry in data:
        if entry['ship_id'] == ship_id and entry['timestamp'] in [9, 10, 11]:
            print(f"  T{entry['timestamp']}: lat={entry['lat']}, lon={entry['lon']}, label={entry['label']}, speed={entry['speed']}, heading={entry['heading']}")
    print()

# Check corridor bounds
print("Corridor bounds from geofence.py:")
print("  LAT: 13.00 - 13.10")
print("  LON: 80.35 - 80.50")
print()

# Check if S5/S6 are inside corridor at each frame
print("Is S5/S6 inside corridor at each frame?")
for ship_id in ['S5', 'S6']:
    print(f"{ship_id}:")
    for entry in data:
        if entry['ship_id'] == ship_id and entry['timestamp'] in [9, 10, 11]:
            lat = entry['lat']
            lon = entry['lon']
            in_corridor = (13.00 <= lat <= 13.10) and (80.35 <= lon <= 80.50)
            print(f"  T{entry['timestamp']}: lat={lat}, lon={lon} -> Inside corridor: {in_corridor}")
    print()
