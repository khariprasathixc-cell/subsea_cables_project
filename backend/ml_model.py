"""
Machine Learning module for anomaly detection using IsolationForest.
Engineers features from ship AIS data and trains an unsupervised model
to detect anomalous behavior patterns.
"""

import json
import math
import numpy as np
from sklearn.ensemble import IsolationForest

# Corridor zone boundaries (same as geofence.py)
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.20
CORRIDOR_LON_MAX = 80.35

# Data source path
DATA_SOURCE = "data/ships_data.json"


def load_mock_data(filepath):
    """
    Load ship AIS data from JSON file.
    
    Args:
        filepath (str): Path to the JSON file
    
    Returns:
        list: List of ship data dictionaries
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def compute_distance_to_corridor(lat, lon):
    """
    Compute the straight-line distance from a point to the nearest edge
    of the corridor rectangle. If inside the corridor, distance = 0.
    
    Args:
        lat (float): Latitude coordinate
        lon (float): Longitude coordinate
    
    Returns:
        float: Distance in degrees (0 if inside corridor)
    """
    # Check if point is inside the corridor
    if (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX and
        CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX):
        return 0.0
    
    # Compute distance to each edge
    dist_lat_min = abs(lat - CORRIDOR_LAT_MIN) if lat < CORRIDOR_LAT_MIN else 0
    dist_lat_max = abs(lat - CORRIDOR_LAT_MAX) if lat > CORRIDOR_LAT_MAX else 0
    dist_lon_min = abs(lon - CORRIDOR_LON_MIN) if lon < CORRIDOR_LON_MIN else 0
    dist_lon_max = abs(lon - CORRIDOR_LON_MAX) if lon > CORRIDOR_LON_MAX else 0
    
    # Distance to nearest edge (Euclidean distance in lat/lon space)
    # If point is outside in both lat and lon, compute diagonal distance
    if lat < CORRIDOR_LAT_MIN and lon < CORRIDOR_LON_MIN:
        return math.sqrt(dist_lat_min**2 + dist_lon_min**2)
    elif lat < CORRIDOR_LAT_MIN and lon > CORRIDOR_LON_MAX:
        return math.sqrt(dist_lat_min**2 + dist_lon_max**2)
    elif lat > CORRIDOR_LAT_MAX and lon < CORRIDOR_LON_MIN:
        return math.sqrt(dist_lat_max**2 + dist_lon_min**2)
    elif lat > CORRIDOR_LAT_MAX and lon > CORRIDOR_LON_MAX:
        return math.sqrt(dist_lat_max**2 + dist_lon_max**2)
    else:
        # Point is outside in only one dimension
        return max(dist_lat_min, dist_lat_max, dist_lon_min, dist_lon_max)


def engineer_features(data):
    """
    Engineer features for each row: speed, heading_change_rate, distance_to_corridor.
    
    Args:
        data (list): List of ship data dictionaries
    
    Returns:
        tuple: (features array, metadata list with ship_id and timestamp)
    """
    # Group data by ship_id to compute heading changes
    ships = {}
    for entry in data:
        ship_id = entry['ship_id']
        if ship_id not in ships:
            ships[ship_id] = []
        ships[ship_id].append(entry)
    
    # Sort each ship's data by timestamp
    for ship_id in ships:
        ships[ship_id].sort(key=lambda x: x['timestamp'])
    
    features = []
    metadata = []
    
    for ship_id, entries in ships.items():
        prev_heading = None
        
        for entry in entries:
            speed = entry['speed']
            lat = entry['lat']
            lon = entry['lon']
            heading = entry['heading']
            
            # Compute heading change rate (0 for first timestamp)
            if prev_heading is None:
                heading_change_rate = 0
            else:
                heading_change_rate = abs(heading - prev_heading)
                # Handle wrap-around (e.g., 359 to 1 should be 2, not 358)
                if heading_change_rate > 180:
                    heading_change_rate = 360 - heading_change_rate
            
            # Compute distance to corridor
            distance_to_corridor = compute_distance_to_corridor(lat, lon)
            
            features.append([speed, heading_change_rate, distance_to_corridor])
            metadata.append({
                'ship_id': ship_id,
                'timestamp': entry['timestamp']
            })
            
            prev_heading = heading
    
    return np.array(features), metadata


def train_isolation_forest(features, contamination=0.15):
    """
    Train IsolationForest on the engineered features.
    
    Args:
        features (np.array): Feature matrix
        contamination (float): Expected proportion of outliers
    
    Returns:
        IsolationForest: Trained model
    """
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(features)
    return model


def compute_anomaly_scores(model, features):
    """
    Compute anomaly scores using decision_function and scale to 0-100.
    
    Args:
        model (IsolationForest): Trained model
        features (np.array): Feature matrix
    
    Returns:
        np.array: Anomaly scores scaled to 0-100 (100 = most anomalous)
    """
    # decision_function returns negative values for anomalies
    raw_scores = model.decision_function(features)
    
    # Min-max scaling to 0-100 range
    # Lower decision_function = more anomalous, so we invert
    min_score = raw_scores.min()
    max_score = raw_scores.max()
    
    if max_score == min_score:
        # All scores are the same
        scaled_scores = np.zeros_like(raw_scores)
    else:
        # Scale: higher decision_function = more normal = lower anomaly score
        # So we invert: (max - score) / (max - min) * 100
        scaled_scores = ((max_score - raw_scores) / (max_score - min_score)) * 100
    
    return scaled_scores


def save_ml_scores(metadata, anomaly_scores, filepath):
    """
    Save ML scores to JSON file.
    
    Args:
        metadata (list): List of metadata dictionaries
        anomaly_scores (np.array): Anomaly scores
        filepath (str): Path to save the JSON file
    """
    ml_scores = []
    for meta, score in zip(metadata, anomaly_scores):
        ml_scores.append({
            'ship_id': meta['ship_id'],
            'timestamp': meta['timestamp'],
            'anomaly_score': round(float(score), 1)
        })
    
    with open(filepath, 'w') as f:
        json.dump(ml_scores, f, indent=2)


def main():
    """
    Main function to run the ML pipeline.
    """
    print("Loading mock data...")
    data = load_mock_data(DATA_SOURCE)
    
    print("Engineering features...")
    features, metadata = engineer_features(data)
    
    print(f"Features shape: {features.shape}")
    print(f"Feature columns: speed, heading_change_rate, distance_to_corridor")
    
    print("Training IsolationForest...")
    model = train_isolation_forest(features, contamination=0.15)
    
    print("Computing anomaly scores...")
    anomaly_scores = compute_anomaly_scores(model, features)
    
    print("Saving ML scores...")
    save_ml_scores(metadata, anomaly_scores, 'backend/ml_scores.json')
    
    # Print summary
    rows_scored = len(anomaly_scores)
    min_score = anomaly_scores.min()
    max_score = anomaly_scores.max()
    avg_score = anomaly_scores.mean()
    
    print(f"\nML Model Summary:")
    print(f"Rows scored: {rows_scored}")
    print(f"Min anomaly_score: {min_score:.1f}")
    print(f"Max anomaly_score: {max_score:.1f}")
    print(f"Avg anomaly_score: {avg_score:.1f}")
    print(f"ML scores saved to backend/ml_scores.json")


if __name__ == "__main__":
    main()
