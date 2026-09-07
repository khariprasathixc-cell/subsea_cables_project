"""
Anomaly detection module for ship AIS data.
Detects potential anchor drag events by identifying ships that maintain
low speed inside the submarine cable corridor for consecutive timestamps.
Integrates live acoustic DAS/piezo hardware confirmation signals.
"""

import os
import sys
import json
import time

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from geofence import is_in_corridor

# File paths
DATA_SOURCE = os.path.join(ROOT_DIR, "data", "ships_data.json")
VIBRATION_SIGNAL_FILE = os.path.join(ROOT_DIR, "hardware_fusion", "vibration_signal.json")
ML_SCORES_FILE = os.path.join(ROOT_DIR, "backend", "ml_scores.json")
ALERTS_FILE = os.path.join(ROOT_DIR, "backend", "alerts.json")

# Physical confirmation decay window in seconds
DECAY_WINDOW_SECONDS = 4.5


def load_mock_data(filepath):
    """Load ship AIS data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def load_ml_scores(filepath):
    """Load ML anomaly scores from JSON file."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        return json.load(f)


def check_physical_confirmation(window_seconds=DECAY_WINDOW_SECONDS):
    """
    Check if a live physical vibration/piezo event was recorded within the decay window.
    Returns: (is_confirmed: bool, signal_data: dict)
    """
    if not os.path.exists(VIBRATION_SIGNAL_FILE):
        return False, {}

    try:
        with open(VIBRATION_SIGNAL_FILE, 'r') as f:
            signal_data = json.load(f)

        if signal_data.get('vibration_detected') is True:
            vibration_timestamp = float(signal_data.get('timestamp', 0))
            now = time.time()
            elapsed = now - vibration_timestamp

            if 0 <= elapsed <= window_seconds:
                return True, signal_data
            else:
                # Auto-reset / decay expired vibration flag
                reset_signal = {
                    "vibration_detected": False,
                    "frequency_hz": signal_data.get("frequency_hz", 0.0),
                    "energy": signal_data.get("energy", 0.0),
                    "timestamp": vibration_timestamp
                }
                tmp_file = VIBRATION_SIGNAL_FILE + ".tmp"
                try:
                    with open(tmp_file, 'w') as tf:
                        json.dump(reset_signal, tf, indent=2)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(tmp_file, VIBRATION_SIGNAL_FILE)
                except Exception:
                    pass
                return False, reset_signal

        return False, signal_data
    except Exception as e:
        # Safe fallback on concurrent read
        return False, {}


def create_ml_score_lookup(ml_scores):
    """Create a lookup dictionary for ML scores keyed by (ship_id, timestamp)."""
    lookup = {}
    for score_entry in ml_scores:
        key = (score_entry['ship_id'], score_entry['timestamp'])
        lookup[key] = score_entry['anomaly_score']
    return lookup


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


def detect_anomalies(ships_data, ml_score_lookup=None, is_physically_confirmed=False, das_metadata=None):
    """
    Detect anchor drag events by checking for consecutive low-speed occurrences inside corridor.
    Correlates with ML confidence scores and bimodal physical confirmation.
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

            # Condition: low speed (<5 kts) AND inside cable corridor
            if speed < 5 and is_in_corridor(lat, lon):
                consecutive_count += 1

                # Trigger alert on 2nd consecutive occurrence
                if consecutive_count >= 2 and not alert_triggered:
                    confidence_score = None
                    if ml_score_lookup:
                        key = (ship_id, timestamp)
                        confidence_score = ml_score_lookup.get(key, None)

                    status = "CONFIRMED (DAS TRANSIENT)" if is_physically_confirmed else "SUSPECTED - AIS ONLY"

                    alert = {
                        "ship_id": ship_id,
                        "timestamp": timestamp,
                        "message": "Possible anchor drag detected: speed dropped below 5 knots inside cable corridor",
                        "confidence_score": confidence_score,
                        "physical_confirmation": bool(is_physically_confirmed),
                        "status": status,
                        "frequency_hz": das_metadata.get("frequency_hz", 0.0) if is_physically_confirmed and das_metadata else None,
                        "energy": das_metadata.get("energy", 0.0) if is_physically_confirmed and das_metadata else None,
                        "last_updated": time.time()
                    }
                    alerts.append(alert)
                    alert_triggered = True
            else:
                consecutive_count = 0

    return alerts


def save_alerts(alerts, filepath):
    """Save alerts to JSON file with atomic replace and flush."""
    tmp_file = filepath + ".tmp"
    with open(tmp_file, 'w') as f:
        json.dump(alerts, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_file, filepath)


def main():
    print("=" * 65)
    print("   SubseaGuard Sentinel-X Bimodal Anomaly Detection Engine")
    print("=" * 65)
    print("Monitoring AIS streams & DAS acoustic hardware signals...")
    print(f"Decay Window: {DECAY_WINDOW_SECONDS}s")
    print(f"Alert Output: {ALERTS_FILE}\n")

    # Load base AIS data
    data = load_mock_data(DATA_SOURCE)
    ships_data = group_by_ship(data)

    # Load ML scores if available
    ml_scores = load_ml_scores(ML_SCORES_FILE)
    ml_score_lookup = create_ml_score_lookup(ml_scores)
    if ml_score_lookup:
        print(f"ML scores loaded: {len(ml_scores)} records.")
    else:
        print("Warning: ml_scores.json not found. Running without ML confidence scores.")

    previous_alerts_str = ""
    last_physical_state = None

    try:
        while True:
            # 1. Check live physical hardware confirmation
            is_physically_confirmed, das_metadata = check_physical_confirmation(DECAY_WINDOW_SECONDS)

            # 2. Run sequential anomaly detector with current hardware fusion state
            alerts = detect_anomalies(
                ships_data=ships_data,
                ml_score_lookup=ml_score_lookup,
                is_physically_confirmed=is_physically_confirmed,
                das_metadata=das_metadata
            )

            # 3. Serialize and detect changes
            # Compare state ignoring last_updated timestamp
            compare_repr = [(a['ship_id'], a['timestamp'], a['status'], a['physical_confirmation']) for a in alerts]
            current_alerts_str = json.dumps(compare_repr)

            if current_alerts_str != previous_alerts_str:
                save_alerts(alerts, ALERTS_FILE)
                previous_alerts_str = current_alerts_str

                timestamp_str = time.strftime('%H:%M:%S')
                if is_physically_confirmed:
                    freq = das_metadata.get('frequency_hz', 0)
                    print(f"[{timestamp_str}] 🔴 DAS HARDWARE TRANSIENT CONFIRMED! Alerts updated -> 'CONFIRMED (DAS TRANSIENT)' (Freq: {freq} Hz)")
                else:
                    if last_physical_state is True:
                        print(f"[{timestamp_str}] ⚪ DAS Transient decayed. Alerts reverted -> 'SUSPECTED - AIS ONLY'")
                    else:
                        print(f"[{timestamp_str}] ⚡ Alerts initialized/updated ({len(alerts)} alerts active)")

                last_physical_state = is_physically_confirmed

            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\nStopping anomaly detection pipeline...")


if __name__ == "__main__":
    main()
