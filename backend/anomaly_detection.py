"""
Anomaly detection module for ship AIS data.
Detects potential anchor drag events by identifying ships that maintain
low speed inside the submarine cable corridor for consecutive timestamps.
"""

import json
from geofence import is_in_corridor


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


def detect_anomalies(ships_data):
    """
    Detect anchor drag events by checking for consecutive low-speed
    occurrences inside the corridor zone.
    
    Args:
        ships_data (dict): Dictionary of ship data grouped by ship_id
    
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
                    alerts.append({
                        "ship_id": ship_id,
                        "timestamp": timestamp,
                        "message": "Possible anchor drag detected: speed dropped below 5 knots inside cable corridor"
                    })
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
    Main function to run the anomaly detection pipeline.
    """
    # Load mock data
    data = load_mock_data('backend/mock_data.json')
    
    # Group by ship and sort by timestamp
    ships_data = group_by_ship(data)
    
    # Detect anomalies
    alerts = detect_anomalies(ships_data)
    
    # Save alerts
    save_alerts(alerts, 'backend/alerts.json')
    
    # Print summary
    ships_checked = len(ships_data)
    alerts_generated = len(alerts)
    alert_ships = [alert['ship_id'] for alert in alerts]
    
    print(f"Ships checked: {ships_checked}")
    print(f"Alerts generated: {alerts_generated}")
    if alert_ships:
        print(f"Ships with alerts: {', '.join(alert_ships)}")
    else:
        print("Ships with alerts: None")


if __name__ == "__main__":
    main()
