"""
Data generator for SubseaGuard AIS demo.
Generates deterministic, mathematically de-conflicted ship trajectory data across 8 vessels (S1-S8)
over 20 timestamps in open water (Bay of Bengal, Longitude >= 80.325E).
"""

import os
import sys
import json
import math

# Protected Cable Corridor boundaries (Bay of Bengal / Chennai corridor)
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.35
CORRIDOR_LON_MAX = 80.50

# Minimum offshore longitude (Bay of Bengal open sea constraint)
MIN_OFFSHORE_LON = 80.325


def is_in_corridor(lat, lon):
    """Check if a coordinate point falls inside the protected cable corridor."""
    return (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX and
            CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX)


def generate_ship_data():
    """
    Generate deterministic, spatially de-conflicted AIS trajectories for 8 vessels (S1 to S8)
    strictly in the open waters of the Bay of Bengal (Longitude >= 80.325E).
    """
    data = []

    # S1: Normal Cargo - Deep South Offshore Lane (Lat 12.905 -> 12.930, Lon 80.330 -> 80.530)
    for t in range(1, 21):
        lat = 12.905 + (t - 1) * 0.0013
        lon = 80.330 + (t - 1) * 0.0105
        speed = 16.2 + (0.3 if t % 2 == 0 else -0.2)
        data.append({
            'ship_id': 'S1',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': 78,
            'label': 'normal',
            'vessel_type': 'cargo'
        })

    # S2: Normal Tanker - Outer Deepwater East Lane (Lat 12.980 -> 13.130, Lon 80.540 -> 80.620)
    for t in range(1, 21):
        lat = 12.980 + (t - 1) * 0.0075
        lon = 80.540 + (t - 1) * 0.0040
        speed = 15.5 + (-0.2 if t % 2 == 0 else 0.3)
        data.append({
            'ship_id': 'S2',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': 28,
            'label': 'normal',
            'vessel_type': 'tanker'
        })

    # S3: Normal Fishing - Mid-South Offshore Lane (Lat 12.945 -> 12.960, Lon 80.400 -> 80.530)
    for t in range(1, 21):
        lat = 12.945 + (t - 1) * 0.0008
        lon = 80.400 + (t - 1) * 0.0068
        speed = 14.2 + (0.2 if t % 3 == 0 else -0.1)
        data.append({
            'ship_id': 'S3',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': 83,
            'label': 'normal',
            'vessel_type': 'fishing'
        })

    # S4: Normal Cargo - North Offshore Lane (Lat 13.145 -> 13.165, Lon 80.330 -> 80.560)
    for t in range(1, 21):
        lat = 13.145 + (t - 1) * 0.0010
        lon = 80.330 + (t - 1) * 0.0120
        speed = 16.8 + (-0.3 if t % 2 == 0 else 0.2)
        data.append({
            'ship_id': 'S4',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': 85,
            'label': 'normal',
            'vessel_type': 'cargo'
        })

    # S5: Anomaly Tanker - Southern/Central Corridor Sector (Anchor Drift ~13.030, ~80.400)
    for t in range(1, 21):
        if t <= 10:
            lat = 13.025 + (t - 1) * 0.0004
            lon = 80.325 + (t - 1) * 0.0022  # at t=10, lon=80.3448 < 80.35 (in open water outside corridor)
            speed = 15.8 - (t - 1) * 0.1
            heading = 85
            label = 'normal'
        else:
            if t == 11:
                speed = 10.5
                lat = 13.029
                lon = 80.348
                heading = 82
            elif t == 12:
                speed = 6.8
                lat = 13.030
                lon = 80.360  # ENTERS corridor
                heading = 80
            elif t == 13:
                speed = 4.2   # Speed < 5 kts inside corridor
                lat = 13.030
                lon = 80.375
                heading = 78
            elif t == 14:
                speed = 3.1
                lat = 13.031
                lon = 80.388
                heading = 76
            elif t == 15:
                speed = 2.4
                lat = 13.032
                lon = 80.398
                heading = 75
            else:
                speed = 1.8 + (t - 16) * 0.1
                lat = 13.032 + (t - 15) * 0.0003
                lon = 80.398 + (t - 15) * 0.0015
                heading = 72
            label = 'anomaly'
        data.append({
            'ship_id': 'S5',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': heading,
            'label': label,
            'vessel_type': 'tanker'
        })

    # S6: Anomaly Fishing - Northern/Eastern Corridor Sector (Anchor Drift ~13.075, ~80.450)
    for t in range(1, 21):
        if t <= 10:
            lat = 13.080 - (t - 1) * 0.0004
            lon = 80.328 + (t - 1) * 0.0020  # at t=10, lon=80.346 < 80.35 (in open water outside corridor)
            speed = 14.6 - (t - 1) * 0.1
            heading = 95
            label = 'normal'
        else:
            if t == 11:
                speed = 9.8
                lat = 13.076
                lon = 80.348
                heading = 98
            elif t == 12:
                speed = 6.2
                lat = 13.075
                lon = 80.368  # ENTERS corridor
                heading = 100
            elif t == 13:
                speed = 4.0   # Speed < 5 kts inside corridor
                lat = 13.075
                lon = 80.395
                heading = 102
            elif t == 14:
                speed = 2.8
                lat = 13.075
                lon = 80.420
                heading = 104
            elif t == 15:
                speed = 2.1
                lat = 13.075
                lon = 80.438
                heading = 105
            else:
                speed = 1.6 + (t - 16) * 0.1
                lat = 13.075 + (t - 15) * 0.0004
                lon = 80.438 + (t - 15) * 0.0020
                heading = 106
            label = 'anomaly'
        data.append({
            'ship_id': 'S6',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': heading,
            'label': label,
            'vessel_type': 'fishing'
        })

    # S7: Near-Miss Fast Cargo - High-Speed Corridor Transit (Lat 13.055, Lon 80.330 -> 80.570)
    for t in range(1, 21):
        lat = 13.055 + (0.0003 if t % 2 == 0 else -0.0003)
        lon = 80.330 + (t - 1) * 0.0125  # Enters corridor at t=3, exits at t=15
        speed = 16.5 + (0.3 if t % 2 == 0 else -0.2)
        heading = 90
        label = 'near_miss' if is_in_corridor(lat, lon) else 'normal'
        data.append({
            'ship_id': 'S7',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': heading,
            'label': label,
            'vessel_type': 'cargo'
        })

    # S8: Near-Miss Slow Tanker - Decelerates strictly south of corridor (Lat 12.975 < 13.00, Lon 80.335 -> 80.365)
    for t in range(1, 21):
        if t <= 8:
            lat = 12.972 + (t - 1) * 0.0004
            lon = 80.335 + (t - 1) * 0.0035
            speed = 15.0 - (t - 1) * 0.2
            heading = 80
            label = 'normal'
        else:
            lat = 12.975 + (0.0002 if t % 2 == 0 else -0.0002)
            lon = 80.360 + (t - 8) * 0.0006
            speed = 2.8 + (0.2 if t % 2 == 0 else -0.1)
            heading = 84
            label = 'near_miss'
        data.append({
            'ship_id': 'S8',
            'timestamp': t,
            'lat': round(lat, 4),
            'lon': round(lon, 4),
            'speed': round(speed, 1),
            'heading': heading,
            'label': label,
            'vessel_type': 'tanker'
        })

    return data


def verify_patterns(data):
    """Comprehensive assertion verification for open sea bounds, trajectory rules, and spatial de-confliction."""
    print("=" * 60)
    print("   OPEN SEA TRAJECTORY & DE-CONFLICTION VERIFICATION")
    print("=" * 60)

    # Group by ship
    ships = {}
    for row in data:
        ship_id = row['ship_id']
        if ship_id not in ships:
            ships[ship_id] = []
        ships[ship_id].append(row)

    issues = []

    # 1. Check Open Water Geographic Boundary (Lon >= 80.325E)
    for row in data:
        if row['lon'] < MIN_OFFSHORE_LON:
            issues.append(f"{row['ship_id']} at T{row['timestamp']}: Coordinate on mainland (Lon {row['lon']} < {MIN_OFFSHORE_LON})")

    # 2. Check Normal Ships (S1-S4)
    for ship_id in ['S1', 'S2', 'S3', 'S4']:
        ship_data = ships[ship_id]
        if any(r['label'] != 'normal' for r in ship_data):
            issues.append(f"{ship_id}: Non-normal label found")
        if any(is_in_corridor(r['lat'], r['lon']) for r in ship_data):
            issues.append(f"{ship_id}: Entered protected corridor zone")
        if any(r['speed'] < 13.0 for r in ship_data):
            issues.append(f"{ship_id}: Cruising speed dropped below threshold")

    # 3. Check Anomaly Ships (S5, S6)
    for ship_id in ['S5', 'S6']:
        ship_data = ships[ship_id]
        labels = [r['label'] for r in ship_data]
        speeds = [r['speed'] for r in ship_data]
        positions = [(r['lat'], r['lon']) for r in ship_data]

        if labels[0:10].count('normal') != 10:
            issues.append(f"{ship_id}: Timestamps 1-10 not all normal")
        if labels[10:].count('anomaly') != 10:
            issues.append(f"{ship_id}: Timestamps 11-20 not all anomaly")
        if speeds[14] >= 5.0:  # timestamp 15
            issues.append(f"{ship_id}: Speed not under 5 knots by timestamp 15")
        if not any(is_in_corridor(lat, lon) for lat, lon in positions[10:]):
            issues.append(f"{ship_id}: Never entered corridor in anomaly phase")

    # 4. Check Near-Miss Ships (S7, S8)
    s7_data = ships['S7']
    s8_data = ships['S8']
    if not any(is_in_corridor(r['lat'], r['lon']) for r in s7_data):
        issues.append("S7: Did not enter corridor for fast transit test")
    if any(r['speed'] < 14.0 for r in s7_data):
        issues.append("S7: Speed dropped below safe transit speed")
    if any(is_in_corridor(r['lat'], r['lon']) for r in s8_data):
        issues.append("S8: Entered corridor (should remain strictly outside)")
    if not any(r['speed'] < 5.0 for r in s8_data[8:]):
        issues.append("S8: Did not decelerate below 5 knots outside corridor")

    # 5. Spatial De-Confliction Verification (Min distance >= 0.015 deg across all pairs at all timestamps)
    min_dist_by_time = {}
    for t in range(1, 21):
        min_dist_t = 999.0
        ship_list = list(ships.keys())
        for i in range(len(ship_list)):
            for j in range(i + 1, len(ship_list)):
                sA = ships[ship_list[i]][t - 1]
                sB = ships[ship_list[j]][t - 1]
                dist = math.sqrt((sA['lat'] - sB['lat'])**2 + (sA['lon'] - sB['lon'])**2)
                if dist < min_dist_t:
                    min_dist_t = dist
                if dist < 0.015:
                    issues.append(f"Collision at T{t} between {ship_list[i]} and {ship_list[j]} (dist: {dist:.4f} deg < 0.015 deg)")
        min_dist_by_time[t] = min_dist_t

    if issues:
        print("\n[FAIL] ISSUES DETECTED:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\n[OK] ALL OPEN WATER INVARIANTS SATISFIED (100% PASS)")
        print(f"  - Total records: {len(data)} (8 ships x 20 timesteps)")
        print(f"  - Longitude Range: [{min(r['lon'] for r in data):.4f}E to {max(r['lon'] for r in data):.4f}E] (Pure Open Sea)")
        print(f"  - Latitude Range: [{min(r['lat'] for r in data):.4f}N to {max(r['lat'] for r in data):.4f}N]")
        print(f"  - Separation at T17-20: { {t: round(min_dist_by_time[t], 4) for t in range(17, 21)} }")
        print("=" * 60)
        return True


def main():
    print("Generating open water de-conflicted AIS dataset (Bay of Bengal)...")
    data = generate_ship_data()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, 'ships_data.json')

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Saved {len(data)} records to {output_path}")

    success = verify_patterns(data)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
