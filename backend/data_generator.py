"""
Data generator for SubseaGuard AIS demo.
Generates realistic ship trajectory data with normal, anomaly, and near-miss behaviors.
"""

import random
import json

# Corridor boundaries (must match geofence.py exactly)
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.20
CORRIDOR_LON_MAX = 80.35

def is_in_corridor(lat, lon):
    """Check if a point is inside the corridor zone."""
    return (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX and
            CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX)

def generate_ship_data():
    """Generate data for 8 ships with different behavioral patterns."""
    
    data = []
    
    # Ship configuration: (ship_id, pattern, vessel_type)
    # Patterns: 'normal', 'anomaly', 'near_miss_fast', 'near_miss_slow'
    ship_configs = [
        ('S1', 'normal', 'cargo'),
        ('S2', 'normal', 'tanker'),
        ('S3', 'normal', 'fishing'),
        ('S4', 'normal', 'cargo'),
        ('S5', 'anomaly', 'tanker'),
        ('S6', 'anomaly', 'fishing'),
        ('S7', 'near_miss_fast', 'cargo'),
        ('S8', 'near_miss_slow', 'tanker'),
    ]
    
    for ship_id, pattern, vessel_type in ship_configs:
        ship_data = generate_single_ship(ship_id, pattern, vessel_type)
        data.extend(ship_data)
    
    return data

def generate_single_ship(ship_id, pattern, vessel_type):
    """Generate trajectory data for a single ship based on its pattern."""
    
    rows = []
    
    if pattern == 'normal':
        rows = generate_normal_ship(ship_id, vessel_type)
    elif pattern == 'anomaly':
        rows = generate_anomaly_ship(ship_id, vessel_type)
    elif pattern == 'near_miss_fast':
        rows = generate_near_miss_fast_ship(ship_id, vessel_type)
    elif pattern == 'near_miss_slow':
        rows = generate_near_miss_slow_ship(ship_id, vessel_type)
    
    return rows

def generate_normal_ship(ship_id, vessel_type):
    """Generate a normal ship: steady speed, never enters corridor."""
    
    rows = []
    
    # Start position outside corridor (south of corridor)
    lat = 12.95 + random.uniform(-0.02, 0.02)
    lon = 80.25 + random.uniform(-0.02, 0.02)
    
    # Heading and speed
    heading = random.randint(30, 60)
    base_speed = random.uniform(14, 18)
    
    for timestamp in range(1, 21):
        # Small heading changes (< 2 degrees)
        heading += random.uniform(-1.5, 1.5)
        
        # Steady speed with minor variation
        speed = base_speed + random.uniform(-0.5, 0.5)
        
        # Move in straight line (small position changes)
        lat += random.uniform(-0.005, 0.005)
        lon += random.uniform(-0.005, 0.005)
        
        # Ensure we stay outside corridor
        if lat > CORRIDOR_LAT_MIN - 0.02:
            lat = CORRIDOR_LAT_MIN - 0.02 - random.uniform(0, 0.01)
        
        row = {
            'ship_id': ship_id,
            'timestamp': timestamp,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': int(round(heading)) % 360,
            'label': 'normal',
            'vessel_type': vessel_type
        }
        rows.append(row)
    
    return rows

def generate_anomaly_ship(ship_id, vessel_type):
    """Generate an anomaly ship: normal then slow drift into corridor."""
    
    rows = []
    
    # Start position outside corridor (west of corridor)
    lat = 13.05 + random.uniform(-0.02, 0.02)
    lon = 80.15 + random.uniform(-0.02, 0.02)
    
    heading = random.randint(70, 100)
    base_speed = random.uniform(14, 18)
    
    for timestamp in range(1, 21):
        if timestamp <= 10:
            # Normal behavior
            heading += random.uniform(-1.5, 1.5)
            speed = base_speed + random.uniform(-0.5, 0.5)
            label = 'normal'
            
            # Normal movement
            lat += random.uniform(-0.005, 0.005)
            lon += random.uniform(0.005, 0.015)
            
        else:
            # Anomaly behavior: speed drops, drifts into corridor
            # Speed drops gradually to under 5 by timestamp 15
            speed_reduction = (timestamp - 10) / 5  # 0.2 to 1.0
            speed = max(1.5, base_speed * (1 - speed_reduction * 0.7))
            
            # Minimal heading changes (drifting)
            heading += random.uniform(-0.5, 0.5)
            
            # Drift into corridor
            lat += random.uniform(-0.002, 0.002)
            lon += random.uniform(0.005, 0.01)
            
            # Ensure we enter corridor by timestamp 12-13
            if timestamp >= 12:
                if lon < CORRIDOR_LON_MIN + 0.02:
                    lon = CORRIDOR_LON_MIN + 0.02 + random.uniform(0, 0.01)
                if lat < CORRIDOR_LAT_MIN:
                    lat = CORRIDOR_LAT_MIN + random.uniform(0, 0.02)
                if lat > CORRIDOR_LAT_MAX:
                    lat = CORRIDOR_LAT_MAX - random.uniform(0, 0.02)
            
            label = 'anomaly'
        
        row = {
            'ship_id': ship_id,
            'timestamp': timestamp,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': int(round(heading)) % 360,
            'label': label,
            'vessel_type': vessel_type
        }
        rows.append(row)
    
    return rows

def generate_near_miss_fast_ship(ship_id, vessel_type):
    """Generate near-miss ship: fast transit through corridor."""
    
    rows = []
    
    # Start position west of corridor
    lat = 13.05 + random.uniform(-0.01, 0.01)
    lon = 80.15 + random.uniform(-0.01, 0.01)
    
    heading = random.randint(80, 100)
    base_speed = random.uniform(15, 18)
    
    for timestamp in range(1, 21):
        # Maintain high speed throughout
        speed = base_speed + random.uniform(-0.5, 0.5)
        
        # Consistent heading
        heading += random.uniform(-1, 1)
        
        # Move eastward through corridor
        lon += random.uniform(0.01, 0.02)
        lat += random.uniform(-0.002, 0.002)
        
        # Determine label based on corridor entry
        if is_in_corridor(lat, lon):
            label = 'near_miss'
        else:
            label = 'normal'
        
        row = {
            'ship_id': ship_id,
            'timestamp': timestamp,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': int(round(heading)) % 360,
            'label': label,
            'vessel_type': vessel_type
        }
        rows.append(row)
    
    return rows

def generate_near_miss_slow_ship(ship_id, vessel_type):
    """Generate near-miss ship: slow speed just outside corridor."""
    
    rows = []
    
    # Start position just outside corridor (south edge)
    lat = CORRIDOR_LAT_MIN - 0.015  # Just outside, within ~0.02 degrees
    lon = 80.27 + random.uniform(-0.01, 0.01)
    
    heading = random.randint(340, 20)
    base_speed = random.uniform(14, 18)
    
    for timestamp in range(1, 21):
        if timestamp <= 8:
            # Normal behavior
            speed = base_speed + random.uniform(-0.5, 0.5)
            label = 'normal'
            lat += random.uniform(-0.005, 0.005)
            lon += random.uniform(-0.005, 0.005)
        else:
            # Slow down but stay just outside corridor
            speed = random.uniform(2.0, 4.5)
            label = 'near_miss'
            
            # Minimal movement, staying just outside
            lat += random.uniform(-0.001, 0.001)
            lon += random.uniform(-0.002, 0.002)
            
            # Ensure we stay just outside (within ~0.02 degrees)
            if lat > CORRIDOR_LAT_MIN - 0.005:
                lat = CORRIDOR_LAT_MIN - 0.01 - random.uniform(0, 0.005)
            if lat < CORRIDOR_LAT_MIN - 0.025:
                lat = CORRIDOR_LAT_MIN - 0.02 + random.uniform(0, 0.005)
        
        heading += random.uniform(-1, 1)
        
        row = {
            'ship_id': ship_id,
            'timestamp': timestamp,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': int(round(heading)) % 360,
            'label': label,
            'vessel_type': vessel_type
        }
        rows.append(row)
    
    return rows

def print_summary(data):
    """Print summary statistics of generated data."""
    
    total_rows = len(data)
    
    # Count labels
    label_counts = {'normal': 0, 'anomaly': 0, 'near_miss': 0}
    ship_categories = {'normal': [], 'anomaly': [], 'near_miss': []}
    
    for row in data:
        label_counts[row['label']] += 1
        ship_id = row['ship_id']
        label = row['label']
        if ship_id not in ship_categories[label]:
            ship_categories[label].append(ship_id)
    
    print("\n" + "="*50)
    print("DATA GENERATION SUMMARY")
    print("="*50)
    print(f"Total rows: {total_rows}")
    print(f"Label distribution:")
    print(f"  - normal: {label_counts['normal']}")
    print(f"  - anomaly: {label_counts['anomaly']}")
    print(f"  - near_miss: {label_counts['near_miss']}")
    print(f"\nShip categorization:")
    print(f"  - Normal ships: {', '.join(sorted(ship_categories['normal']))}")
    print(f"  - Anomaly ships: {', '.join(sorted(ship_categories['anomaly']))}")
    print(f"  - Near-miss ships: {', '.join(sorted(ship_categories['near_miss']))}")
    print("="*50 + "\n")

def main():
    """Main function to generate and save ship data."""
    
    print("Generating ship data...")
    data = generate_ship_data()
    
    # Save to JSON file
    output_path = 'data/ships_data.json'
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Data saved to {output_path}")
    
    # Print summary
    print_summary(data)
    
    # Verify patterns
    verify_patterns(data)

def verify_patterns(data):
    """Verify that ships follow their intended patterns."""
    
    print("Pattern verification:")
    
    # Group by ship
    ships = {}
    for row in data:
        ship_id = row['ship_id']
        if ship_id not in ships:
            ships[ship_id] = []
        ships[ship_id].append(row)
    
    issues = []
    
    for ship_id, ship_data in ships.items():
        labels = [row['label'] for row in ship_data]
        speeds = [row['speed'] for row in ship_data]
        positions = [(row['lat'], row['lon']) for row in ship_data]
        
        # Check normal ships
        if ship_id in ['S1', 'S2', 'S3', 'S4']:
            if any(label != 'normal' for label in labels):
                issues.append(f"{ship_id}: Non-normal label found")
            if any(is_in_corridor(lat, lon) for lat, lon in positions):
                issues.append(f"{ship_id}: Entered corridor")
        
        # Check anomaly ships
        elif ship_id in ['S5', 'S6']:
            if labels[0:10].count('normal') != 10:
                issues.append(f"{ship_id}: First 10 timestamps not all normal")
            if labels[10:].count('anomaly') != 10:
                issues.append(f"{ship_id}: Last 10 timestamps not all anomaly")
            if speeds[14] >= 5:  # timestamp 15 (index 14)
                issues.append(f"{ship_id}: Speed not under 5 knots by timestamp 15")
            if not any(is_in_corridor(lat, lon) for lat, lon in positions[10:]):
                issues.append(f"{ship_id}: Never entered corridor in anomaly phase")
        
        # Check near-miss ships
        elif ship_id in ['S7', 'S8']:
            if 'near_miss' not in labels:
                issues.append(f"{ship_id}: No near_miss labels found")
    
    if issues:
        print("  Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  All patterns verified successfully!")

if __name__ == "__main__":
    main()
