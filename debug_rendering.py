import json

# Load ships data
with open('data/ships_data.json', 'r') as f:
    data = json.load(f)

# Check S5 and S6 coordinates around frames 10-11
for ship_id in ['S5', 'S6']:
    print(f"\n{ship_id} coordinates frames 8-13:")
    for entry in data:
        if entry['ship_id'] == ship_id and 8 <= entry['timestamp'] <= 13:
            print(f"  T{entry['timestamp']}: lat={entry['lat']}, lon={entry['lon']}, label={entry['label']}")
