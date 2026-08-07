import random
import json

def generate_mock_data():
    data = []
    
    # Overall offshore bounds (Bay of Bengal, east of Chennai coastline)
    offshore_lat_min, offshore_lat_max = 12.95, 13.20
    offshore_lon_min, offshore_lon_max = 80.30, 80.65
    
    # Corridor zone boundaries (sub-range within offshore bounds)
    corridor_lat_min, corridor_lat_max = 13.00, 13.10
    corridor_lon_min, corridor_lon_max = 80.35, 80.50
    
    # Vessel types
    vessel_types = ["cargo", "fishing", "tanker"]
    
    # Generate data for S1-S4 (normal behavior - never enter corridor)
    for ship_id in ["S1", "S2", "S3", "S4"]:
        # Start position within offshore bounds (outside corridor zone)
        lat = random.uniform(offshore_lat_min, offshore_lat_max)
        lon = random.uniform(offshore_lon_min, offshore_lon_max)
        speed = random.uniform(14, 18)
        heading = random.uniform(0, 360)
        vessel_type = random.choice(vessel_types)
        
        for timestamp in range(1, 21):
            # Update position (moving in straight line, staying away from corridor)
            lat += random.uniform(-0.01, 0.01)
            lon += random.uniform(-0.01, 0.01)
            
            # Ensure stays outside corridor
            if corridor_lat_min <= lat <= corridor_lat_max and corridor_lon_min <= lon <= corridor_lon_max:
                # Push out of corridor
                if lat < (corridor_lat_min + corridor_lat_max) / 2:
                    lat = corridor_lat_min - 0.02
                else:
                    lat = corridor_lat_max + 0.02
            
            # Speed stays steady between 14-18 knots
            speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
            
            # Heading changes by no more than 2 degrees
            heading += random.uniform(-2, 2)
            heading = heading % 360
            
            # Validate coordinates are within offshore bounds
            if lon < offshore_lon_min:
                raise ValueError(f"Invalid longitude {lon} for {ship_id} at timestamp {timestamp}: below minimum {offshore_lon_min}")
            if lat < offshore_lat_min or lat > offshore_lat_max:
                raise ValueError(f"Invalid latitude {lat} for {ship_id} at timestamp {timestamp}: outside range [{offshore_lat_min}, {offshore_lat_max}]")
            
            data.append({
                "ship_id": ship_id,
                "timestamp": timestamp,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "speed": round(speed, 1),
                "heading": round(heading),
                "label": "normal",
                "vessel_type": vessel_type
            })
    
    # Generate data for S5-S6 (anomaly behavior - enter corridor, speed drops)
    for ship_id in ["S5", "S6"]:
        # Start position within offshore bounds (outside corridor zone)
        lat = random.uniform(offshore_lat_min, offshore_lat_max)
        lon = random.uniform(offshore_lon_min, offshore_lon_max)
        speed = random.uniform(14, 18)
        heading = random.uniform(0, 360)
        vessel_type = random.choice(vessel_types)
        
        for timestamp in range(1, 21):
            label = "normal"
            
            if timestamp >= 11:
                label = "anomaly"
                # Speed drops gradually to under 5 knots by timestamp 15
                if timestamp <= 15:
                    progress = (timestamp - 11) / 4  # 0 to 1
                    target_speed = 15 - progress * 12  # 15 down to 3
                    speed = min(target_speed, speed - random.uniform(1.0, 2.0))
                else:
                    speed = max(1.5, speed - random.uniform(0.5, 1.0))
                
                # Lat/lon drifts toward and through corridor zone
                # Use stronger drift to ensure entering corridor
                corridor_center_lat = (corridor_lat_min + corridor_lat_max) / 2
                corridor_center_lon = (corridor_lon_min + corridor_lon_max) / 2
                
                lat += (corridor_center_lat - lat) * 0.2 + random.uniform(-0.001, 0.001)
                lon += (corridor_center_lon - lon) * 0.2 + random.uniform(-0.001, 0.001)
            else:
                # Normal behavior for timestamps 1-10
                speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
                heading += random.uniform(-2, 2)
                heading = heading % 360
                lat += random.uniform(-0.01, 0.01)
                lon += random.uniform(-0.01, 0.01)
            
            # Validate coordinates are within offshore bounds
            if lon < offshore_lon_min:
                raise ValueError(f"Invalid longitude {lon} for {ship_id} at timestamp {timestamp}: below minimum {offshore_lon_min}")
            if lat < offshore_lat_min or lat > offshore_lat_max:
                raise ValueError(f"Invalid latitude {lat} for {ship_id} at timestamp {timestamp}: outside range [{offshore_lat_min}, {offshore_lat_max}]")
            
            data.append({
                "ship_id": ship_id,
                "timestamp": timestamp,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "speed": round(speed, 1),
                "heading": round(heading),
                "label": label,
                "vessel_type": vessel_type
            })
    
    # Generate data for S7-S8 (near_miss behavior)
    for i, ship_id in enumerate(["S7", "S8"]):
        # Start position within offshore bounds (outside corridor zone)
        lat = random.uniform(offshore_lat_min, offshore_lat_max)
        lon = random.uniform(offshore_lon_min, offshore_lon_max)
        speed = random.uniform(14, 18)
        heading = random.uniform(0, 360)
        vessel_type = random.choice(vessel_types)
        
        for timestamp in range(1, 21):
            # S7: enters corridor without speed drop
            # S8: speed drops without entering corridor
            if i == 0 and timestamp >= 11:
                label = "near_miss"
                # Enter corridor but maintain speed
                corridor_center_lat = (corridor_lat_min + corridor_lat_max) / 2
                corridor_center_lon = (corridor_lon_min + corridor_lon_max) / 2
                
                lat += (corridor_center_lat - lat) * 0.1 + random.uniform(-0.002, 0.002)
                lon += (corridor_center_lon - lon) * 0.1 + random.uniform(-0.002, 0.002)
                speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
            elif i == 1 and timestamp >= 11:
                label = "near_miss"
                # Drop speed but stay outside corridor
                speed = max(2, speed - random.uniform(2.0, 3.0))
                lat += random.uniform(-0.01, 0.01)
                lon += random.uniform(-0.01, 0.01)
                
                # Ensure stays outside corridor
                if corridor_lat_min <= lat <= corridor_lat_max and corridor_lon_min <= lon <= corridor_lon_max:
                    # Push out of corridor
                    if lat < (corridor_lat_min + corridor_lat_max) / 2:
                        lat = corridor_lat_min - 0.02
                    else:
                        lat = corridor_lat_max + 0.02
            else:
                label = "normal"
                speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
                heading += random.uniform(-2, 2)
                heading = heading % 360
                lat += random.uniform(-0.01, 0.01)
                lon += random.uniform(-0.01, 0.01)
            
            # Validate coordinates are within offshore bounds
            if lon < offshore_lon_min:
                raise ValueError(f"Invalid longitude {lon} for {ship_id} at timestamp {timestamp}: below minimum {offshore_lon_min}")
            if lat < offshore_lat_min or lat > offshore_lat_max:
                raise ValueError(f"Invalid latitude {lat} for {ship_id} at timestamp {timestamp}: outside range [{offshore_lat_min}, {offshore_lat_max}]")
            
            data.append({
                "ship_id": ship_id,
                "timestamp": timestamp,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "speed": round(speed, 1),
                "heading": round(heading),
                "label": label,
                "vessel_type": vessel_type
            })
    
    # Save to JSON file
    output_path = "data/ships_data.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Print summary
    total_rows = len(data)
    normal_count = sum(1 for item in data if item["label"] == "normal")
    anomaly_count = sum(1 for item in data if item["label"] == "anomaly")
    near_miss_count = sum(1 for item in data if item["label"] == "near_miss")
    
    print(f"Total rows generated: {total_rows}")
    print(f"Normal labels: {normal_count}")
    print(f"Anomaly labels: {anomaly_count}")
    print(f"Near_miss labels: {near_miss_count}")
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    generate_mock_data()
