"""
Anomaly detection module for ship AIS data.
Detects potential anchor drag events by identifying ships that maintain
low speed inside the submarine cable corridor for consecutive timestamps.
"""

import json
from geofence import is_in_corridor

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


def load_ml_scores(filepath):
    """
    Load ML anomaly scores from JSON file.
    
    Args:
        filepath (str): Path to the JSON file
    
    Returns:
        list: List of ML score dictionaries
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def create_ml_score_lookup(ml_scores):
    """
    Create a lookup dictionary for ML scores keyed by ship_id and timestamp.
    
    Args:
        ml_scores (list): List of ML score dictionaries
    
    Returns:
        dict: Lookup dictionary with (ship_id, timestamp) as key
    """
    lookup = {}
    for score_entry in ml_scores:
        key = (score_entry['ship_id'], score_entry['timestamp'])
        lookup[key] = score_entry['anomaly_score']
    return lookup


def group_by_ship(data):
    """
    Group data by ship_id and sort by timestamp.
    
    Args:
        data (list): List of ship data dictionaries
    
    Returns:
        dict: Dictionary with ship_id as key and sorted list of timestamps as value
    """
    ships = {}
    for entry in data:
        ship_id = entry['ship_id']
        if ship_id not in ships:
            ships[ship_id] = []
        ships[ship_id].append(entry)
    
    # Sort each ship's data by timestamp
    for ship_id in ships:
        ships[ship_id].sort(key=lambda x: x['timestamp'])
    
    return ships


def detect_anomalies(ships_data, ml_score_lookup=None):
    """
    Detect anchor drag events by checking for consecutive low-speed
    occurrences inside the corridor zone. Optionally adds ML confidence scores.
    
    Args:
        ships_data (dict): Dictionary of ship data grouped by ship_id
        ml_score_lookup (dict): Optional lookup dictionary for ML scores
    
    Returns:
        list: List of alert dictionaries
    """
    alerts = []
    
    for ship_id, entries in ships_data.items():
        consecutive_count = 0
        alert_triggered = False
        
        for entry in entries:
            timestamp = entry['timestamp']
            speed = entry['speed']
            lat = entry['lat']
            lon = entry['lon']
            
            # Check both conditions: low speed AND inside corridor
            if speed < 5 and is_in_corridor(lat, lon):
                consecutive_count += 1
                
                # Trigger alert on the second consecutive occurrence
                if consecutive_count >= 2 and not alert_triggered:
                    # Look up ML confidence score if available
                    confidence_score = None
                    if ml_score_lookup:
                        key = (ship_id, timestamp)
                        confidence_score = ml_score_lookup.get(key, None)
                    
                    alert = {
                        "ship_id": ship_id,
                        "timestamp": timestamp,
                        "message": "Possible anchor drag detected: speed dropped below 5 knots inside cable corridor",
                        "confidence_score": confidence_score
                    }
                    alerts.append(alert)
                    alert_triggered = True
            else:
                # Reset counter if conditions are not met
                consecutive_count = 0
    
    return alerts


def save_alerts(alerts, filepath):
    """
    Save alerts to JSON file.
    
    Args:
        alerts (list): List of alert dictionaries
        filepath (str): Path to save the JSON file
    """
    with open(filepath, 'w') as f:
        json.dump(alerts, f, indent=2)


def main():
    """
    Main function to run the anomaly detection pipeline with ML integration.
    """
    # Load mock data
    data = load_mock_data(DATA_SOURCE)
    
    # Group by ship and sort by timestamp
    ships_data = group_by_ship(data)
    
    # Load ML scores if available
    ml_score_lookup = None
    ml_scores = []
    try:
        ml_scores = load_ml_scores('backend/ml_scores.json')
        ml_score_lookup = create_ml_score_lookup(ml_scores)
        print("ML scores loaded successfully.")
    except FileNotFoundError:
        print("Warning: ml_scores.json not found. Running without ML confidence scores.")
    
    # Detect anomalies (with ML scores if available)
    alerts = detect_anomalies(ships_data, ml_score_lookup)
    
    # Save alerts
    save_alerts(alerts, 'backend/alerts.json')
    
    # Print summary
    ships_checked = len(ships_data)
    alerts_generated = len(alerts)
    alert_ships = [alert['ship_id'] for alert in alerts]
    alerts_with_confidence = sum(1 for alert in alerts if alert['confidence_score'] is not None)
    
    print(f"\nAnomaly Detection Summary:")
    print(f"Ships checked: {ships_checked}")
    print(f"Alerts generated: {alerts_generated}")
    if alert_ships:
        print(f"Ships with alerts: {', '.join(alert_ships)}")
    else:
        print("Ships with alerts: None")
    
    # Print ML statistics if scores were loaded
    if ml_scores:
        rows_scored = len(ml_scores)
        scores = [s['anomaly_score'] for s in ml_scores]
        min_score = min(scores)
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        
        print(f"\nML Model Statistics:")
        print(f"Rows scored by ML: {rows_scored}")
        print(f"Min anomaly_score: {min_score:.1f}")
        print(f"Max anomaly_score: {max_score:.1f}")
        print(f"Avg anomaly_score: {avg_score:.1f}")
        print(f"Alerts with confidence_score: {alerts_with_confidence}")


if __name__ == "__main__":
    main()
