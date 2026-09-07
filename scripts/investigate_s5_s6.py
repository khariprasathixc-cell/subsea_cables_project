import json
import math

# Load ships data
with open('data/ships_data.json', 'r') as f:
    ships_data = json.load(f)

# Load ML scores
with open('backend/ml_scores.json', 'r') as f:
    ml_scores = json.load(f)

# Corridor bounds
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.35
CORRIDOR_LON_MAX = 80.50

def distance_to_corridor(lat, lon):
    """Calculate minimum distance from point to corridor rectangle."""
    # Find closest point on corridor rectangle
    closest_lat = max(CORRIDOR_LAT_MIN, min(lat, CORRIDOR_LAT_MAX))
    closest_lon = max(CORRIDOR_LON_MIN, min(lon, CORRIDOR_LON_MAX))
    return math.sqrt((lat - closest_lat)**2 + (lon - closest_lon)**2)

# Find S5 and S6 at timestamp 16
print("=== S5 and S6 Data at Timestamp 16 ===\n")

features = {}

for ship_id in ['S5', 'S6']:
    print(f"Ship {ship_id}:")
    
    # Find data at timestamp 16
    entry = None
    for row in ships_data:
        if row['ship_id'] == ship_id and row['timestamp'] == 16:
            entry = row
            break
    
    if entry:
        print(f"  Raw data: lat={entry['lat']}, lon={entry['lon']}, speed={entry['speed']}, heading={entry['heading']}, label={entry['label']}")
        
        # Calculate heading change rate (compare to timestamp 15)
        entry_15 = None
        for row in ships_data:
            if row['ship_id'] == ship_id and row['timestamp'] == 15:
                entry_15 = row
                break
        
        heading_change_rate = 0
        if entry_15:
            heading_change = abs(entry['heading'] - entry_15['heading'])
            if heading_change > 180:
                heading_change = 360 - heading_change
            heading_change_rate = heading_change
            print(f"  Heading change from t15: {heading_change} degrees")
            print(f"  Heading change rate: {heading_change_rate}")
        
        # Calculate distance to corridor
        dist_to_corridor = distance_to_corridor(entry['lat'], entry['lon'])
        print(f"  Distance to corridor: {dist_to_corridor:.4f} degrees")
        
        # Find ML score
        for score_entry in ml_scores:
            if score_entry['ship_id'] == ship_id and score_entry['timestamp'] == 16:
                print(f"  ML anomaly_score: {score_entry['anomaly_score']}")
                break
        
        # Store features for comparison
        features[ship_id] = {
            'speed': entry['speed'],
            'heading_change_rate': heading_change_rate,
            'distance_to_corridor': dist_to_corridor,
            'anomaly_score': score_entry['anomaly_score'] if score_entry else None
        }
    else:
        print(f"  No data found at timestamp 16")
    
    print()

# Check if S5 and S6 have identical feature values at timestamp 16
print("=== Comparing S5 and S6 Features at Timestamp 16 ===\n")

if 'S5' in features and 'S6' in features:
    s5 = features['S5']
    s6 = features['S6']
    
    print(f"S5 speed: {s5['speed']:.4f}")
    print(f"S6 speed: {s6['speed']:.4f}")
    print(f"Speed match: {abs(s5['speed'] - s6['speed']) < 0.001}")
    print()
    print(f"S5 heading_change_rate: {s5['heading_change_rate']:.4f}")
    print(f"S6 heading_change_rate: {s6['heading_change_rate']:.4f}")
    print(f"Heading change rate match: {abs(s5['heading_change_rate'] - s6['heading_change_rate']) < 0.001}")
    print()
    print(f"S5 distance_to_corridor: {s5['distance_to_corridor']:.4f}")
    print(f"S6 distance_to_corridor: {s6['distance_to_corridor']:.4f}")
    print(f"Distance to corridor match: {abs(s5['distance_to_corridor'] - s6['distance_to_corridor']) < 0.001}")
    print()
    print(f"S5 anomaly_score: {s5['anomaly_score']}")
    print(f"S6 anomaly_score: {s6['anomaly_score']}")
    print(f"Anomaly score match: {s5['anomaly_score'] == s6['anomaly_score']}")
    print()
    
    if (abs(s5['speed'] - s6['speed']) < 0.001 and
        abs(s5['heading_change_rate'] - s6['heading_change_rate']) < 0.001 and
        abs(s5['distance_to_corridor'] - s6['distance_to_corridor']) < 0.001):
        print("CONCLUSION: S5 and S6 have IDENTICAL feature values at timestamp 16, which explains the identical confidence scores.")
        print("This is likely due to the deterministic random seed or similar randomization in the data generation for both anomaly ships.")
    else:
        print("CONCLUSION: S5 and S6 have DIFFERENT feature values, so identical confidence scores may indicate a scaling or calculation issue.")
