import json

with open('data/ships_data.json', 'r') as f:
    data = json.load(f)

s5_entries = [e for e in data if e['ship_id'] == 'S5']
s6_entries = [e for e in data if e['ship_id'] == 'S6']

print(f'S5 entries: {len(s5_entries)}')
print(f'S6 entries: {len(s6_entries)}')
print(f'S5 timestamps: {sorted([e["timestamp"] for e in s5_entries])}')
print(f'S6 timestamps: {sorted([e["timestamp"] for e in s6_entries])}')
print(f'S5 null lat/lon: {sum(1 for e in s5_entries if e.get("lat") is None or e.get("lon") is None)}')
print(f'S6 null lat/lon: {sum(1 for e in s6_entries if e.get("lat") is None or e.get("lon") is None)}')

# Check for any missing timestamps
s5_timestamps = set(e['timestamp'] for e in s5_entries)
s6_timestamps = set(e['timestamp'] for e in s6_entries)
all_timestamps = set(range(1, 21))

print(f'S5 missing timestamps: {sorted(all_timestamps - s5_timestamps)}')
print(f'S6 missing timestamps: {sorted(all_timestamps - s6_timestamps)}')
