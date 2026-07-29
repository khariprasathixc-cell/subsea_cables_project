import random
import json

def generate_mock_data():
    data = []
    
    # Corridor zone boundaries
    corridor_lat_min, corridor_lat_max = 13.00, 13.10
    corridor_lon_min, corridor_lon_max = 80.20, 80.35
    
    # Generate data for S1 and S2 (normal behavior)
    for ship_id in ["S1", "S2"]:
        # Start position outside corridor zone
        lat = 13.05 + random.uniform(-0.05, 0.05)
        lon = 80.28 + random.uniform(-0.05, 0.05)
        speed = random.uniform(14, 18)
        heading = random.uniform(0, 360)
        
        for timestamp in range(1, 21):
            # Update position (moving in straight line away from corridor)
            lat += random.uniform(-0.01, 0.01)
            lon += random.uniform(-0.01, 0.01)
            
            # Speed stays steady between 14-18 knots
            speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
            
            # Heading changes by no more than 2 degrees
            heading += random.uniform(-2, 2)
            heading = heading % 360
            
            data.append({
                "ship_id": ship_id,
                "timestamp": timestamp,
                "lat": round(lat, 2),
                "lon": round(lon, 2),
                "speed": round(speed, 1),
                "heading": round(heading),
                "label": "normal"
            })
    
    # Generate data for S3 and S4 (anomaly behavior)
    for ship_id in ["S3", "S4"]:
        # Start position outside corridor zone
        lat = 13.05 + random.uniform(-0.05, 0.05)
        lon = 80.28 + random.uniform(-0.05, 0.05)
        speed = random.uniform(14, 18)
        heading = random.uniform(0, 360)
        
        for timestamp in range(1, 21):
            label = "normal"
            
            if timestamp >= 11:
                label = "anomaly"
                # Speed drops gradually to under 3 knots by timestamp 15
                # Linear interpolation: from ~15 at t=11 to <3 at t=15
                if timestamp <= 15:
                    progress = (timestamp - 11) / 4  # 0 to 1
                    target_speed = 15 - progress * 12  # 15 down to 3
                    speed = min(target_speed, speed - random.uniform(1.0, 2.0))
                else:
                    speed = max(1.5, speed - random.uniform(0.5, 1.0))
                
                # Lat/lon drifts toward and through corridor zone
                # Move toward center of corridor (13.05, 80.275)
                corridor_center_lat = (corridor_lat_min + corridor_lat_max) / 2
                corridor_center_lon = (corridor_lon_min + corridor_lon_max) / 2
                
                lat += (corridor_center_lat - lat) * 0.1 + random.uniform(-0.002, 0.002)
                lon += (corridor_center_lon - lon) * 0.1 + random.uniform(-0.002, 0.002)
            else:
                # Normal behavior for timestamps 1-10
                speed = max(14, min(18, speed + random.uniform(-0.5, 0.5)))
                heading += random.uniform(-2, 2)
                heading = heading % 360
                lat += random.uniform(-0.01, 0.01)
                lon += random.uniform(-0.01, 0.01)
            
            data.append({
                "ship_id": ship_id,
                "timestamp": timestamp,
                "lat": round(lat, 2),
                "lon": round(lon, 2),
                "speed": round(speed, 1),
                "heading": round(heading),
                "label": label
            })
    
    # Save to JSON file
    output_path = "backend/mock_data.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Print summary
    total_rows = len(data)
    normal_count = sum(1 for item in data if item["label"] == "normal")
    anomaly_count = sum(1 for item in data if item["label"] == "anomaly")
    
    print(f"Total rows generated: {total_rows}")
    print(f"Normal labels: {normal_count}")
    print(f"Anomaly labels: {anomaly_count}")
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    generate_mock_data()
