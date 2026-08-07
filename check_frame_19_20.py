import json

with open('data/ships_data.json', 'r') as f:
    data = json.load(f)

print("=== Data at frames 19 and 20 ===\n")
for timestamp in [19, 20]:
    print(f"Timestamp {timestamp}:")
    for entry in data:
        if entry['timestamp'] == timestamp:
            print(f"  {entry['ship_id']}: lat={entry['lat']}, lon={entry['lon']}, label={entry['label']}")
    print()
