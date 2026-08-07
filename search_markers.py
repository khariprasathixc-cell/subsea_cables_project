import re

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print("=== STEP 1: Find every marker creation instance ===\n")

# Search for L.marker(
print("L.marker( instances:")
for i, line in enumerate(lines, 1):
    if 'L.marker(' in line:
        print(f"  Line {i}: {line.strip()}")

print("\nL.circleMarker( instances:")
for i, line in enumerate(lines, 1):
    if 'L.circleMarker(' in line:
        print(f"  Line {i}: {line.strip()}")

print("\nL.divIcon( instances:")
for i, line in enumerate(lines, 1):
    if 'L.divIcon(' in line:
        print(f"  Line {i}: {line.strip()}")

print("\n=== STEP 2: Check for hardcoded/invalid coordinates ===\n")
print("Searching for hardcoded coordinates like [0,0], undefined, etc:")
for i, line in enumerate(lines, 1):
    if re.search(r'\[0,\s*0\]', line):
        print(f"  Line {i}: {line.strip()}")
    if re.search(r'undefined', line):
        print(f"  Line {i}: {line.strip()}")

print("\n=== STEP 3: Find clearLayers() calls ===\n")
print("clearLayers() instances:")
for i, line in enumerate(lines, 1):
    if 'clearLayers()' in line:
        print(f"  Line {i}: {line.strip()}")
