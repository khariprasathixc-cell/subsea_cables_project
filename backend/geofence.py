"""
Geofence module for submarine cable corridor detection.
Defines the rectangular corridor zone and provides a function to check
if a coordinate falls inside it.
"""

# Corridor zone boundaries (rectangular box - offshore Bay of Bengal)
# Overall offshore bounds: LAT 12.95-13.20, LON 80.30-80.65
# Corridor is a sub-range within these bounds
CORRIDOR_LAT_MIN = 13.00
CORRIDOR_LAT_MAX = 13.10
CORRIDOR_LON_MIN = 80.35
CORRIDOR_LON_MAX = 80.50


def is_in_corridor(lat, lon):
    """
    Check if a given latitude/longitude point falls inside the corridor zone.
    
    Args:
        lat (float): Latitude coordinate
        lon (float): Longitude coordinate
    
    Returns:
        bool: True if point is inside the corridor, False otherwise
    """
    return (CORRIDOR_LAT_MIN <= lat <= CORRIDOR_LAT_MAX and
            CORRIDOR_LON_MIN <= lon <= CORRIDOR_LON_MAX)


if __name__ == "__main__":
    # Test the function with a few sample coordinates
    test_points = [
        (13.05, 80.42),  # Inside corridor
        (13.00, 80.35),  # On edge (inside)
        (13.10, 80.50),  # On edge (inside)
        (12.99, 80.42),  # Outside (lat too low)
        (13.05, 80.34),  # Outside (lon too low)
        (13.11, 80.42),  # Outside (lat too high)
        (13.05, 80.51),  # Outside (lon too high)
    ]
    
    print("Testing is_in_corridor function:")
    print(f"Corridor zone: lat [{CORRIDOR_LAT_MIN}, {CORRIDOR_LAT_MAX}], lon [{CORRIDOR_LON_MIN}, {CORRIDOR_LON_MAX}]")
    print()
    
    for lat, lon in test_points:
        result = is_in_corridor(lat, lon)
        print(f"({lat}, {lon}): {result}")
