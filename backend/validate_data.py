"""
Validation script for data/ships_data.json
Checks label sequences and behavior against expected categories.
"""

import json

# Corridor zone boundaries
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.20
CORRIDOR_LON_MAX = 80.35

def is_in_corridor(lat, lon):
    """Check if point is inside corridor zone."""
    return (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX and
            CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX)

def load_data(filepath):
    """Load ship data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def group_by_ship(data):
    """Group data by ship_id and sort by timestamp."""
    ships = {}
    for entry in data:
        ship_id = entry['ship_id']
        if ship_id not in ships:
            ships[ship_id] = []
        ships[ship_id].append(entry)
    
    for ship_id in ships:
        ships[ship_id].sort(key=lambda x: x['timestamp'])
    
    return ships

def validate_label_sequences(ships_data):
    """Step 1: Validate label sequences for each ship."""
    print("=" * 80)
    print("STEP 1: VALIDATE LABEL SEQUENCES")
    print("=" * 80)
    
    errors = []
    
    for ship_id in sorted(ships_data.keys()):
        entries = ships_data[ship_id]
        labels = [e['label'] for e in entries]
        
        normal_count = labels.count('normal')
        anomaly_count = labels.count('anomaly')
        near_miss_count = labels.count('near_miss')
        
        print(f"\n{ship_id}: normal x{normal_count}, anomaly x{anomaly_count}, near_miss x{near_miss_count}")
        
        # Check if labels match expected pattern
        if ship_id in ['S1', 'S2', 'S3', 'S4']:
            # Should be fully normal
            if normal_count != 20:
                errors.append(f"{ship_id}: Expected 20 normal labels, got {normal_count}")
        elif ship_id in ['S5', 'S6']:
            # Should be normal 1-10, anomaly 11-20
            if normal_count != 10 or anomaly_count != 10:
                errors.append(f"{ship_id}: Expected 10 normal + 10 anomaly, got {normal_count} normal + {anomaly_count} anomaly")
            # Check sequence
            expected = ['normal'] * 10 + ['anomaly'] * 10
            if labels != expected:
                errors.append(f"{ship_id}: Label sequence incorrect. Expected normal(1-10) then anomaly(11-20)")
        elif ship_id in ['S7', 'S8']:
            # Should be near_miss (pattern varies)
            if near_miss_count == 0:
                errors.append(f"{ship_id}: Expected near_miss labels, got none")
    
    if errors:
        print("\n" + "=" * 80)
        print("LABEL VALIDATION ERRORS:")
        print("=" * 80)
        for error in errors:
            print(f"  ❌ {error}")
        return False
    else:
        print("\n✅ All label sequences are correct.")
        return True

def validate_anomaly_ships(ships_data):
    """Step 2: Validate anomaly ships behavior."""
    print("\n" + "=" * 80)
    print("STEP 2: VALIDATE ANOMALY SHIPS (S5, S6)")
    print("=" * 80)
    
    errors = []
    
    for ship_id in ['S5', 'S6']:
        if ship_id not in ships_data:
            continue
        
        entries = ships_data[ship_id]
        anomaly_entries = [e for e in entries if e['timestamp'] >= 11]
        
        print(f"\n{ship_id} timestamps 11-20:")
        speed_below_5_by_15 = False
        in_corridor_during_window = False
        
        for entry in anomaly_entries:
            ts = entry['timestamp']
            speed = entry['speed']
            lat = entry['lat']
            lon = entry['lon']
            in_corridor = is_in_corridor(lat, lon)
            
            print(f"  t{ts}: speed={speed}, lat={lat}, lon={lon}, in_corridor={in_corridor}")
            
            if ts == 15 and speed < 5:
                speed_below_5_by_15 = True
            if in_corridor:
                in_corridor_during_window = True
        
        if not speed_below_5_by_15:
            errors.append(f"{ship_id}: Speed not below 5 knots by timestamp 15")
        if not in_corridor_during_window:
            errors.append(f"{ship_id}: Never entered corridor zone during anomaly window")
    
    if errors:
        print("\n" + "=" * 80)
        print("ANOMALY SHIP VALIDATION ERRORS:")
        print("=" * 80)
        for error in errors:
            print(f"  ❌ {error}")
        return False
    else:
        print("\n✅ Anomaly ships validated successfully.")
        return True

def validate_near_miss_ships(ships_data):
    """Step 3: Validate near_miss ships behavior."""
    print("\n" + "=" * 80)
    print("STEP 3: VALIDATE NEAR_MISS SHIPS (S7, S8)")
    print("=" * 80)
    
    errors = []
    
    for ship_id in ['S7', 'S8']:
        if ship_id not in ships_data:
            continue
        
        entries = ships_data[ship_id]
        
        print(f"\n{ship_id} all timestamps:")
        entered_corridor = False
        speed_below_5 = False
        both_conditions = False
        
        for entry in entries:
            ts = entry['timestamp']
            speed = entry['speed']
            lat = entry['lat']
            lon = entry['lon']
            in_corridor = is_in_corridor(lat, lon)
            
            print(f"  t{ts}: speed={speed}, in_corridor={in_corridor}")
            
            if in_corridor:
                entered_corridor = True
            if speed < 5:
                speed_below_5 = True
            if in_corridor and speed < 5:
                both_conditions = True
        
        # For near_miss ships, they should NOT have both conditions simultaneously
        if both_conditions:
            errors.append(f"{ship_id}: Has both speed < 5 AND in_corridor - should be near_miss, not anomaly")
        
        # Check if one enters corridor without speed drop, or speed drops without entering corridor
        if entered_corridor and not speed_below_5:
            print(f"  → {ship_id}: Enters corridor without speed drop (valid near_miss)")
        elif speed_below_5 and not entered_corridor:
            print(f"  → {ship_id}: Speed drops without entering corridor (valid near_miss)")
        elif not entered_corridor and not speed_below_5:
            errors.append(f"{ship_id}: Neither enters corridor nor drops speed - invalid near_miss")
    
    if errors:
        print("\n" + "=" * 80)
        print("NEAR_MISS SHIP VALIDATION ERRORS:")
        print("=" * 80)
        for error in errors:
            print(f"  ❌ {error}")
        return False
    else:
        print("\n✅ Near_miss ships validated successfully.")
        return True

def validate_normal_ships(ships_data):
    """Step 4: Validate normal ships don't enter corridor."""
    print("\n" + "=" * 80)
    print("STEP 4: VALIDATE NORMAL SHIPS (S1, S2, S3, S4)")
    print("=" * 80)
    
    errors = []
    
    for ship_id in ['S1', 'S2', 'S3', 'S4']:
        if ship_id not in ships_data:
            continue
        
        entries = ships_data[ship_id]
        entered_corridor = False
        
        for entry in entries:
            lat = entry['lat']
            lon = entry['lon']
            if is_in_corridor(lat, lon):
                entered_corridor = True
                ts = entry['timestamp']
                errors.append(f"{ship_id}: Entered corridor at timestamp {ts} (lat={lat}, lon={lon})")
        
        if not entered_corridor:
            print(f"  ✅ {ship_id}: Never entered corridor")
    
    if errors:
        print("\n" + "=" * 80)
        print("NORMAL SHIP VALIDATION ERRORS:")
        print("=" * 80)
        for error in errors:
            print(f"  ❌ {error}")
        return False
    else:
        print("\n✅ Normal ships validated successfully.")
        return True

def main():
    """Run all validation steps."""
    print("\n" + "=" * 80)
    print("VALIDATION REPORT FOR data/ships_data.json")
    print("=" * 80)
    
    data = load_data('data/ships_data.json')
    ships_data = group_by_ship(data)
    
    # Run all validation steps
    step1_pass = validate_label_sequences(ships_data)
    step2_pass = validate_anomaly_ships(ships_data)
    step3_pass = validate_near_miss_ships(ships_data)
    step4_pass = validate_normal_ships(ships_data)
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Step 1 (Label Sequences): {'✅ PASS' if step1_pass else '❌ FAIL'}")
    print(f"Step 2 (Anomaly Ships): {'✅ PASS' if step2_pass else '❌ FAIL'}")
    print(f"Step 3 (Near_Miss Ships): {'✅ PASS' if step3_pass else '❌ FAIL'}")
    print(f"Step 4 (Normal Ships): {'✅ PASS' if step4_pass else '❌ FAIL'}")
    print("=" * 80)
    
    if step1_pass and step2_pass and step3_pass and step4_pass:
        print("\n✅ ALL VALIDATION STEPS PASSED - Dataset is clean.")
        return True
    else:
        print("\n❌ VALIDATION FAILED - Dataset has errors that need fixing.")
        return False

if __name__ == "__main__":
    main()
